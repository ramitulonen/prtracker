from datetime import datetime, timezone
from typing import Any

from prtracker.config import LOOKBACK_DAYS, TRACKED_REPOS
from prtracker.github_client import build_level_2_query, build_repo_query, run_github_query
from prtracker.helpers import days_since, display_author_name
from prtracker.models import (
    AuthorPRGroup,
    AuthorSummary,
    Level1ViewData,
    Level2AuthorViewData,
    Level2RepoViewData,
    PRSummary,
    RecentAction,
    RepoPRGroup,
    RepoSummary,
)

def commit_actor(commit_node: dict[str, Any]) -> str:
    authors = (
        commit_node.get("commit", {})
        .get("authors", {})
        .get("nodes", [])
    )

    if not authors:
        return "unknown"

    first_author = authors[0]
    user = first_author.get("user")

    if user and user.get("login"):
        return user["login"]

    if first_author.get("name"):
        return first_author["name"]

    return "unknown"


def build_recent_actions(pr: dict[str, Any]) -> list[RecentAction]:
    actions: list[RecentAction] = []

    for node in pr.get("commits", {}).get("nodes", []):
        commit = node.get("commit")
        if not commit:
            continue

        committed_date = commit.get("committedDate")
        if not committed_date:
            continue

        actions.append(
            RecentAction(
                created_at=committed_date,
                action_type="commit",
                actor=commit_actor(node),
                text=commit.get("messageHeadline", "").strip() or "commit",
            )
        )

    for item in pr.get("timelineItems", {}).get("nodes", []):
        created_at = item.get("createdAt")
        if not created_at:
            continue

        typename = item.get("__typename")

        if typename == "ReviewRequestedEvent":
            actions.append(
                RecentAction(
                    created_at=created_at,
                    action_type="review_request",
                    actor=item.get("actor", {}).get("login") or "unknown",
                    text="requested review",
                )
            )

        elif typename == "PullRequestReview":
            state = item.get("state", "REVIEWED")
            actions.append(
                RecentAction(
                    created_at=created_at,
                    action_type="review",
                    actor=item.get("author", {}).get("login") or "unknown",
                    text=f"review: {state}",
                )
            )

        elif typename == "IssueComment":
            actions.append(
                RecentAction(
                    created_at=created_at,
                    action_type="comment",
                    actor=item.get("author", {}).get("login") or "unknown",
                    text="commented",
                )
            )

    actions = [
        action for action in actions
        if days_since(action.created_at) <= LOOKBACK_DAYS
    ]

    actions.sort(key=lambda action: action.created_at, reverse=True)
    return actions


def pr_from_node(node: dict[str, Any], state: str) -> PRSummary:
    author = "unknown"
    if node.get("author") and node["author"].get("login"):
        author = node["author"]["login"]

    return PRSummary(
        repo=node["repository"]["name"],
        number=node["number"],
        title=node["title"],
        author=author,
        state=state,
        url=node["url"],
        created_at=node["createdAt"],
        updated_at=node["updatedAt"],
        merged_at=node.get("mergedAt"),
        review_decision=node.get("reviewDecision"),
        recent_actions=build_recent_actions(node),
    )


def fetch_level_1_data() -> Level1ViewData:
    all_prs: list[dict[str, Any]] = []

    for repo in TRACKED_REPOS:
        query = build_repo_query(repo)
        data = run_github_query(query)
        prs = data["data"]["search"]["nodes"]
        all_prs.extend(prs)

    repo_grouped: dict[str, dict[str, Any]] = {}
    author_grouped: dict[str, dict[str, Any]] = {}

    for pr in all_prs:
        repo = pr["repository"]["name"]

        author = "unknown"
        if pr.get("author") and pr["author"].get("login"):
            author = pr["author"]["login"]

        idle_days = days_since(pr["updatedAt"])
        is_active = idle_days <= LOOKBACK_DAYS

        if repo not in repo_grouped:
            repo_grouped[repo] = {
                "open_total": 0,
                "active": 0,
                "inactive": 0,
                "last_activity_days": None,
                "authors": {},
            }

        repo_grouped[repo]["open_total"] += 1

        if is_active:
            repo_grouped[repo]["active"] += 1

            current = repo_grouped[repo]["last_activity_days"]
            if current is None or idle_days < current:
                repo_grouped[repo]["last_activity_days"] = idle_days
        else:
            repo_grouped[repo]["inactive"] += 1

        repo_authors = repo_grouped[repo]["authors"]

        if author not in repo_authors:
            repo_authors[author] = {
                "open_count": 0,
                "active_count": 0,
                "inactive_count": 0,
                "last_activity_days": None,
            }

        repo_authors[author]["open_count"] += 1

        if is_active:
            repo_authors[author]["active_count"] += 1
            current = repo_authors[author]["last_activity_days"]
            if current is None or idle_days < current:
                repo_authors[author]["last_activity_days"] = idle_days
        else:
            repo_authors[author]["inactive_count"] += 1

        if author not in author_grouped:
            author_grouped[author] = {
                "open_count": 0,
                "active_count": 0,
                "inactive_count": 0,
                "last_activity_days": None,
            }

        author_grouped[author]["open_count"] += 1

        if is_active:
            author_grouped[author]["active_count"] += 1
            current = author_grouped[author]["last_activity_days"]
            if current is None or idle_days < current:
                author_grouped[author]["last_activity_days"] = idle_days
        else:
            author_grouped[author]["inactive_count"] += 1

    repos: list[RepoSummary] = []

    for repo, repo_data in repo_grouped.items():
        author_rows = [
            AuthorSummary(
                author=author,
                open_count=author_data["open_count"],
                active_count=author_data["active_count"],
                inactive_count=author_data["inactive_count"],
                last_activity_days=author_data["last_activity_days"],
            )
            for author, author_data in repo_data["authors"].items()
            if author_data["last_activity_days"] is not None
        ]

        author_rows.sort(
            key=lambda row: (
                -row.active_count,
                -row.open_count,
                row.last_activity_days if row.last_activity_days is not None else 999,
                display_author_name(row.author).lower(),
            )
        )

        repos.append(
            RepoSummary(
                repo=repo,
                open_total_count=repo_data["open_total"],
                active_count=repo_data["active"],
                inactive_count=repo_data["inactive"],
                last_activity_days=repo_data["last_activity_days"],
                authors=author_rows,
            )
        )

    repos.sort(
        key=lambda row: (
            row.last_activity_days is None,
            row.last_activity_days if row.last_activity_days is not None else 999,
            -row.active_count,
            -row.open_total_count,
            row.repo.lower(),
        )
    )

    authors = [
        AuthorSummary(
            author=author,
            open_count=author_data["open_count"],
            active_count=author_data["active_count"],
            inactive_count=author_data["inactive_count"],
            last_activity_days=author_data["last_activity_days"],
        )
        for author, author_data in author_grouped.items()
        if author_data["last_activity_days"] is not None
    ]

    authors.sort(
        key=lambda row: (
            row.last_activity_days if row.last_activity_days is not None else 999,
            -row.active_count,
            -row.open_count,
            display_author_name(row.author).lower(),
        )
    )

    return Level1ViewData(
        repos=repos,
        authors=authors,
        fetched_at=datetime.now(timezone.utc),
        total_open_prs=len(all_prs),
        in_scope_open_prs=sum(repo.active_count for repo in repos),
        total_repos=len(repos),
        total_authors=len(authors),
    )


def fetch_level_2_repo_data(repo: str) -> Level2RepoViewData:
    query = build_level_2_query(repo)
    data = run_github_query(query)

    open_nodes = data["data"]["openPrs"]["nodes"]
    merged_nodes = data["data"]["mergedPrs"]["nodes"]

    open_prs = [
        pr_from_node(node, "open")
        for node in open_nodes
        if node.get("updatedAt") and days_since(node["updatedAt"]) <= LOOKBACK_DAYS
    ]

    merged_prs = [
        pr_from_node(node, "merged")
        for node in merged_nodes
    ]

    grouped: dict[str, dict[str, list[PRSummary]]] = {}

    for pr in open_prs:
        grouped.setdefault(pr.author, {"open": [], "merged": []})
        grouped[pr.author]["open"].append(pr)

    for pr in merged_prs:
        grouped.setdefault(pr.author, {"open": [], "merged": []})
        grouped[pr.author]["merged"].append(pr)

    groups: list[AuthorPRGroup] = []

    for author, values in grouped.items():
        values["open"].sort(key=lambda pr: days_since(pr.updated_at))
        values["merged"].sort(key=lambda pr: pr.merged_at or pr.updated_at, reverse=True)

        groups.append(
            AuthorPRGroup(
                author=author,
                open_prs=values["open"],
                merged_prs=values["merged"],
            )
        )

    groups.sort(
        key=lambda group: (
            -(len(group.open_prs) + len(group.merged_prs)),
            display_author_name(group.author).lower(),
        )
    )

    return Level2RepoViewData(
        repo=repo,
        groups=groups,
        fetched_at=datetime.now(timezone.utc),
        open_count=len(open_prs),
        merged_count=len(merged_prs),
    )


def fetch_level_2_author_data(author: str) -> Level2AuthorViewData:
    all_open_prs: list[PRSummary] = []
    all_merged_prs: list[PRSummary] = []

    for repo in TRACKED_REPOS:
        repo_data = fetch_level_2_repo_data(repo)

        for group in repo_data.groups:
            if group.author != author:
                continue

            all_open_prs.extend(group.open_prs)
            all_merged_prs.extend(group.merged_prs)

    grouped: dict[str, dict[str, list[PRSummary]]] = {}

    for pr in all_open_prs:
        grouped.setdefault(pr.repo, {"open": [], "merged": []})
        grouped[pr.repo]["open"].append(pr)

    for pr in all_merged_prs:
        grouped.setdefault(pr.repo, {"open": [], "merged": []})
        grouped[pr.repo]["merged"].append(pr)

    groups: list[RepoPRGroup] = []

    for repo, values in grouped.items():
        values["open"].sort(key=lambda pr: days_since(pr.updated_at))
        values["merged"].sort(key=lambda pr: pr.merged_at or pr.updated_at, reverse=True)

        groups.append(
            RepoPRGroup(
                repo=repo,
                open_prs=values["open"],
                merged_prs=values["merged"],
            )
        )

    groups.sort(
        key=lambda group: (
            -(len(group.open_prs) + len(group.merged_prs)),
            group.repo.lower(),
        )
    )

    return Level2AuthorViewData(
        author=author,
        groups=groups,
        fetched_at=datetime.now(timezone.utc),
        open_count=len(all_open_prs),
        merged_count=len(all_merged_prs),
    )
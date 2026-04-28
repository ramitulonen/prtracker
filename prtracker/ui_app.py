from typing import Any

from rich.text import Text

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widgets import DataTable, Footer, Header, Static

from prtracker.cache import SimpleCache
from prtracker.config import LOOKBACK_DAYS, MAX_CACHE_ENTRIES
from prtracker.data_fetching import (
    fetch_level_1_data,
    fetch_level_2_author_data,
    fetch_level_2_repo_data,
)
from prtracker.helpers import (
    days_since,
    display_author_name,
    format_fetched_at,
    idle_style,
    parse_github_datetime,
)
from prtracker.models import (
    Level1ViewData,
    Level2AuthorViewData,
    Level2RepoViewData,
    PRSummary,
)


# ============================================================
# APP
# ============================================================

class PRTrackerApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }

    #topbar {
        height: 3;
        padding: 0 1;
        content-align: left middle;
    }

    #main {
        height: 1fr;
    }

    #left_panel {
        width: 45%;
        padding: 0 1 1 1;
    }

    #right_panel {
        width: 55%;
        padding: 0 1 1 1;
        border-left: solid $accent;
    }

    DataTable {
        height: 1fr;
    }

    #details_scroll {
        height: 1fr;
    }

    #details {
        height: auto;
        padding: 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("right", "open_selected", "Open"),
        Binding("left", "back", "Back"),
        Binding("escape", "back", "Back"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.cache = SimpleCache(MAX_CACHE_ENTRIES)

        self.level = 1
        self.loading = False

        self.level_1_data: Level1ViewData | None = None
        self.level_2_data: Level2RepoViewData | Level2AuthorViewData | None = None

        self.selected_repo: str | None = None
        self.selected_author: str | None = None
        self.selected_pr: PRSummary | None = None
        self.selected_level_1_type: str | None = None

        self.level_1_rows: dict[str, dict[str, Any]] = {}
        self.level_2_rows: dict[str, dict[str, Any]] = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("Loading...", id="topbar")

        with Horizontal(id="main"):
            with Vertical(id="left_panel"):
                yield DataTable(id="main_table")

            with Vertical(id="right_panel"):
                with ScrollableContainer(id="details_scroll"):
                    yield Static("Select item", id="details")

        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#main_table", DataTable)
        table.cursor_type = "row"
        self.load_level_1()

    def action_refresh(self) -> None:
        if self.loading:
            return

        # 🔹 Tyhjennä koko cache ennen fetchiä
        self.cache.clear()

        if self.level == 1:
            self.refresh_level_1()

        elif self.level == 2:
            if isinstance(self.level_2_data, Level2RepoViewData):
                self.refresh_level_2_repo(self.level_2_data.repo)

            elif isinstance(self.level_2_data, Level2AuthorViewData):
                self.refresh_level_2_author(self.level_2_data.author)

    def action_open_selected(self) -> None:
        if self.loading:
            return

        if self.level == 1:
            if self.selected_level_1_type == "repo" and self.selected_repo:
                self.load_level_2_repo(self.selected_repo)
            elif self.selected_level_1_type == "author" and self.selected_author:
                self.load_level_2_author(self.selected_author)

        elif self.level == 2 and self.selected_pr:
            self.notify("Level 3 not implemented yet", severity="warning")

    def action_back(self) -> None:
        if self.loading:
            return

        if self.level == 2:
            self.level = 1
            self.level_2_data = None
            self.selected_pr = None
            self.render_level_1()
            if self.level_1_data:
                self.update_topbar_level_1(self.level_1_data, from_cache=True)

    def load_level_1(self) -> None:
        cached = self.cache.get("level_1")
        if cached is not None:
            self.level_1_data = cached
            self.level = 1
            self.render_level_1()
            self.update_topbar_level_1(cached, from_cache=True)
            return

        self.refresh_level_1()

    def refresh_level_1(self) -> None:
        self.set_loading("Level 1", "Fetching repo and author summary from GitHub...")
        self.fetch_level_1_worker()

    @work(thread=True)
    def fetch_level_1_worker(self) -> None:
        try:
            data = fetch_level_1_data()
        except Exception as e:
            self.call_from_thread(self.handle_fetch_error, str(e))
            return

        self.call_from_thread(self.apply_level_1_data, data)

    def apply_level_1_data(self, data: Level1ViewData) -> None:
        self.loading = False
        self.level_1_data = data
        self.cache.set("level_1", data)
        self.level = 1

        if self.selected_level_1_type is None:
            if data.repos:
                self.selected_level_1_type = "repo"
                self.selected_repo = data.repos[0].repo
            elif data.authors:
                self.selected_level_1_type = "author"
                self.selected_author = data.authors[0].author

        self.render_level_1()
        self.update_topbar_level_1(data, from_cache=False)

    def load_level_2_repo(self, repo: str) -> None:
        key = f"level_2_repo:{repo}"
        cached = self.cache.get(key)

        if cached is not None:
            self.level_2_data = cached
            self.level = 2
            self.render_level_2()
            self.update_topbar_level_2(cached, from_cache=True)
            return

        self.refresh_level_2_repo(repo)

    def refresh_level_2_repo(self, repo: str) -> None:
        self.set_loading("Level 2", f"Fetching PRs for repo {repo} from GitHub...")
        self.fetch_level_2_repo_worker(repo)

    @work(thread=True)
    def fetch_level_2_repo_worker(self, repo: str) -> None:
        try:
            data = fetch_level_2_repo_data(repo)
        except Exception as e:
            self.call_from_thread(self.handle_fetch_error, str(e))
            return

        self.call_from_thread(self.apply_level_2_data, data)

    def load_level_2_author(self, author: str) -> None:
        key = f"level_2_author:{author}"
        cached = self.cache.get(key)

        if cached is not None:
            self.level_2_data = cached
            self.level = 2
            self.render_level_2()
            self.update_topbar_level_2(cached, from_cache=True)
            return

        self.refresh_level_2_author(author)

    def refresh_level_2_author(self, author: str) -> None:
        self.set_loading(
            "Level 2",
            f"Fetching PRs for author {display_author_name(author)} from GitHub..."
        )
        self.fetch_level_2_author_worker(author)

    @work(thread=True)
    def fetch_level_2_author_worker(self, author: str) -> None:
        try:
            data = fetch_level_2_author_data(author)
        except Exception as e:
            self.call_from_thread(self.handle_fetch_error, str(e))
            return

        self.call_from_thread(self.apply_level_2_data, data)

    def apply_level_2_data(self, data: Level2RepoViewData | Level2AuthorViewData) -> None:
        self.loading = False
        self.level_2_data = data
        self.level = 2
        self.selected_pr = None

        if isinstance(data, Level2RepoViewData):
            self.cache.set(f"level_2_repo:{data.repo}", data)
            self.selected_repo = data.repo
            self.selected_level_1_type = "repo"
        else:
            self.cache.set(f"level_2_author:{data.author}", data)
            self.selected_author = data.author
            self.selected_level_1_type = "author"

        self.render_level_2()
        self.update_topbar_level_2(data, from_cache=False)

    def handle_fetch_error(self, error: str) -> None:
        self.loading = False
        self.notify(f"Refresh failed: {error}", severity="error")
        self.update_topbar_error(error)

    def set_loading(self, level_name: str, message: str) -> None:
        self.loading = True
        self.query_one("#topbar", Static).update(
            f"{level_name} | ⏳ {message}"
        )
        self.query_one("#details", Static).update(
            Text(f"⏳ {message}", style="bold yellow")
        )

    def render_level_1(self) -> None:
        if self.level_1_data is None:
            return

        table = self.query_one("#main_table", DataTable)
        table.clear(columns=True)
        table.add_columns("ITEM", "OPEN", "ACTIVE", "INACTIVE", "LAST ACTIVITY")

        self.level_1_rows = {}

        table.add_row(
            Text("REPOSITORIES", style="bold"),
            "",
            "",
            "",
            "",
            key="section:repos",
        )
        self.level_1_rows["section:repos"] = {"type": "section"}

        for repo in self.level_1_data.repos:
            key = f"repo:{repo.repo}"

            if repo.last_activity_days is None:
                last_activity_text = Text("-", style="dim")
            else:
                last_activity_text = Text(
                    f"{repo.last_activity_days}d",
                    style=idle_style(repo.last_activity_days),
                )

            table.add_row(
                f"  {repo.repo}",
                str(repo.open_total_count),
                str(repo.active_count),
                str(repo.inactive_count),
                last_activity_text,
                key=key,
            )

            self.level_1_rows[key] = {
                "type": "repo",
                "repo": repo.repo,
            }

        table.add_row(
            Text("AUTHORS", style="bold"),
            "",
            "",
            "",
            "",
            key="section:authors",
        )
        self.level_1_rows["section:authors"] = {"type": "section"}

        for author in self.level_1_data.authors:
            key = f"author:{author.author}"

            if author.last_activity_days is None:
                last_activity_text = Text("-", style="dim")
            else:
                last_activity_text = Text(
                    f"{author.last_activity_days}d",
                    style=idle_style(author.last_activity_days),
                )

            table.add_row(
                f"  {display_author_name(author.author)}",
                str(author.open_count),
                str(author.active_count),
                str(author.inactive_count),
                last_activity_text,
                key=key,
            )

            self.level_1_rows[key] = {
                "type": "author",
                "author": author.author,
            }

        self.update_level_1_details()

    def render_level_2(self) -> None:
        if self.level_2_data is None:
            return

        if isinstance(self.level_2_data, Level2RepoViewData):
            self.render_level_2_repo()
        else:
            self.render_level_2_author()

    def render_level_2_repo(self) -> None:
        if not isinstance(self.level_2_data, Level2RepoViewData):
            return

        table = self.query_one("#main_table", DataTable)
        table.clear(columns=True)
        table.add_columns("ITEM", "AUTHOR", "INFO")

        self.level_2_rows = {}

        for group in self.level_2_data.groups:
            author_key = f"author:{group.author}"

            table.add_row(
                Text(display_author_name(group.author), style="bold"),
                "",
                f"open {len(group.open_prs)} | merged {len(group.merged_prs)}",
                key=author_key,
            )

            self.level_2_rows[author_key] = {
                "type": "author",
                "author": group.author,
            }

            self.add_pr_rows_to_level_2_table(table, group.open_prs, group.merged_prs)

        self.update_level_2_details_empty()

    def render_level_2_author(self) -> None:
        if not isinstance(self.level_2_data, Level2AuthorViewData):
            return

        table = self.query_one("#main_table", DataTable)
        table.clear(columns=True)
        table.add_columns("ITEM", "REPO", "INFO")

        self.level_2_rows = {}

        for group in self.level_2_data.groups:
            repo_key = f"repo:{group.repo}"

            table.add_row(
                Text(group.repo, style="bold"),
                "",
                f"open {len(group.open_prs)} | merged {len(group.merged_prs)}",
                key=repo_key,
            )

            self.level_2_rows[repo_key] = {
                "type": "repo",
                "repo": group.repo,
            }

            self.add_pr_rows_to_level_2_table(table, group.open_prs, group.merged_prs)

        self.update_level_2_details_empty()

    def add_pr_rows_to_level_2_table(
        self,
        table: DataTable,
        open_prs: list[PRSummary],
        merged_prs: list[PRSummary],
    ) -> None:
        if open_prs:
            section_key = f"section:open:{open_prs[0].repo}:{open_prs[0].author}"
            table.add_row(
                Text("  OPEN", style="bold"),
                "",
                "",
                key=section_key,
            )
            self.level_2_rows[section_key] = {"type": "section"}

            for pr in open_prs:
                pr_key = f"pr:{pr.state}:{pr.repo}:{pr.number}"

                idle = days_since(pr.updated_at)
                idle_text = Text(f"{idle}d", style=idle_style(idle))

                table.add_row(
                    f"    #{pr.number} {pr.title[:50]}",
                    display_author_name(pr.author),
                    idle_text,
                    key=pr_key,
                )

                self.level_2_rows[pr_key] = {
                    "type": "pr",
                    "pr": pr,
                }

        if merged_prs:
            section_key = f"section:merged:{merged_prs[0].repo}:{merged_prs[0].author}"
            table.add_row(
                Text("  MERGED (14d)", style="bold green"),
                "",
                "",
                key=section_key,
            )
            self.level_2_rows[section_key] = {"type": "section"}

            for pr in merged_prs:
                pr_key = f"pr:{pr.state}:{pr.repo}:{pr.number}"

                table.add_row(
                    Text(f"    #{pr.number} {pr.title[:50]}", style="green"),
                    Text(display_author_name(pr.author), style="green"),
                    Text("merged", style="green"),
                    key=pr_key,
                )

                self.level_2_rows[pr_key] = {
                    "type": "pr",
                    "pr": pr,
                }

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if self.loading:
            return

        if event.data_table.id != "main_table":
            return

        key = str(event.row_key.value)

        if self.level == 1:
            row = self.level_1_rows.get(key)
            if not row:
                return

            if row["type"] == "repo":
                self.selected_repo = row["repo"]
                self.selected_level_1_type = "repo"
                self.load_level_2_repo(row["repo"])

            elif row["type"] == "author":
                self.selected_author = row["author"]
                self.selected_level_1_type = "author"
                self.load_level_2_author(row["author"])

        elif self.level == 2:
            row = self.level_2_rows.get(key)
            if row and row["type"] == "pr":
                self.selected_pr = row["pr"]
                self.notify("Level 3 not implemented yet", severity="warning")

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id != "main_table":
            return

        key = str(event.row_key.value)

        if self.level == 1:
            row = self.level_1_rows.get(key)
            if not row:
                return

            if row["type"] == "repo":
                self.selected_repo = row["repo"]
                self.selected_author = None
                self.selected_level_1_type = "repo"
                self.update_level_1_details()

            elif row["type"] == "author":
                self.selected_author = row["author"]
                self.selected_repo = None
                self.selected_level_1_type = "author"
                self.update_level_1_details()

        elif self.level == 2:
            row = self.level_2_rows.get(key)
            if not row:
                return

            if row["type"] == "pr":
                self.selected_pr = row["pr"]
                self.update_pr_preview(self.selected_pr)

            elif row["type"] == "author":
                self.selected_pr = None
                self.update_author_details(row["author"])

            elif row["type"] == "repo":
                self.selected_pr = None
                self.update_repo_details(row["repo"])

            elif row["type"] == "section":
                self.selected_pr = None
                self.update_level_2_details_empty()

    def update_level_1_details(self) -> None:
        details = self.query_one("#details", Static)

        if self.level_1_data is None:
            details.update("No data")
            return

        if self.selected_level_1_type == "repo" and self.selected_repo:
            repo = next(
                (repo for repo in self.level_1_data.repos if repo.repo == self.selected_repo),
                None,
            )

            if repo is None:
                details.update("Repo not found")
                return

            text = Text()
            text.append(f"{repo.repo}\n", style="bold")
            text.append("\n")
            text.append(f"Open total: {repo.open_total_count}\n")
            text.append(f"Active ({LOOKBACK_DAYS}d): {repo.active_count}\n")
            text.append(f"Inactive: {repo.inactive_count}\n")
            text.append("Last activity: ")

            if repo.last_activity_days is None:
                text.append("-\n", style="dim")
            else:
                text.append(
                    f"{repo.last_activity_days}d\n",
                    style=idle_style(repo.last_activity_days),
                )

            text.append("\n")
            text.append("Active authors:\n", style="bold")

            if not repo.authors:
                text.append("  no active authors\n", style="dim")
            else:
                for author in repo.authors:
                    display_name = display_author_name(author.author)

                    text.append(f"  {display_name:25} ")
                    text.append(f"{author.open_count:>3} PR   ")
                    text.append("last activity ")

                    if author.last_activity_days is None:
                        text.append("-\n", style="dim")
                    else:
                        text.append(
                            f"{author.last_activity_days}d\n",
                            style=idle_style(author.last_activity_days),
                        )

            details.update(text)
            return

        if self.selected_level_1_type == "author" and self.selected_author:
            author = next(
                (author for author in self.level_1_data.authors if author.author == self.selected_author),
                None,
            )

            if author is None:
                details.update("Author not found")
                return

            text = Text()
            text.append(display_author_name(author.author), style="bold")
            text.append("\n\n")
            text.append(f"Open total: {author.open_count}\n")
            text.append(f"Active ({LOOKBACK_DAYS}d): {author.active_count}\n")
            text.append(f"Inactive: {author.inactive_count}\n")
            text.append("Last activity: ")

            if author.last_activity_days is None:
                text.append("-\n", style="dim")
            else:
                text.append(
                    f"{author.last_activity_days}d\n",
                    style=idle_style(author.last_activity_days),
                )

            text.append("\n")
            text.append("Open this author to see PRs across all tracked repos.")

            details.update(text)
            return

        details.update("Select repository or author")

    def update_level_2_details_empty(self) -> None:
        details = self.query_one("#details", Static)

        if self.level_2_data is None:
            details.update("No data")
            return

        text = Text()

        if isinstance(self.level_2_data, Level2RepoViewData):
            text.append(f"Repo: {self.level_2_data.repo}\n", style="bold")
        else:
            text.append(f"Author: {display_author_name(self.level_2_data.author)}\n", style="bold")

        text.append("\n")
        text.append(f"Open PRs active within last {LOOKBACK_DAYS}d: {self.level_2_data.open_count}\n")
        text.append(f"Merged PRs within last {LOOKBACK_DAYS}d: ")
        text.append(f"{self.level_2_data.merged_count}\n", style="green")
        text.append("\n")
        text.append("Select a group or PR from the left list.")

        details.update(text)

    def update_author_details(self, author: str) -> None:
        details = self.query_one("#details", Static)

        if not isinstance(self.level_2_data, Level2RepoViewData):
            return

        group = next(
            (group for group in self.level_2_data.groups if group.author == author),
            None,
        )

        if group is None:
            details.update("Author not found")
            return

        text = Text()
        text.append(display_author_name(author), style="bold")
        text.append("\n\n")
        text.append(f"Repo: {self.level_2_data.repo}\n")
        text.append(f"Open PRs: {len(group.open_prs)}\n")
        text.append("Merged PRs: ")
        text.append(f"{len(group.merged_prs)}\n", style="green")

        if group.open_prs:
            last_activity = min(days_since(pr.updated_at) for pr in group.open_prs)
            text.append("Last activity: ")
            text.append(f"{last_activity}d\n", style=idle_style(last_activity))

        details.update(text)

    def update_repo_details(self, repo: str) -> None:
        details = self.query_one("#details", Static)

        if not isinstance(self.level_2_data, Level2AuthorViewData):
            return

        group = next(
            (group for group in self.level_2_data.groups if group.repo == repo),
            None,
        )

        if group is None:
            details.update("Repo not found")
            return

        text = Text()
        text.append(repo, style="bold")
        text.append("\n\n")
        text.append(f"Author: {display_author_name(self.level_2_data.author)}\n")
        text.append(f"Open PRs: {len(group.open_prs)}\n")
        text.append("Merged PRs: ")
        text.append(f"{len(group.merged_prs)}\n", style="green")

        if group.open_prs:
            last_activity = min(days_since(pr.updated_at) for pr in group.open_prs)
            text.append("Last activity: ")
            text.append(f"{last_activity}d\n", style=idle_style(last_activity))

        details.update(text)

    def update_pr_preview(self, pr: PRSummary) -> None:
        details = self.query_one("#details", Static)

        text = Text()
        title_style = "bold green" if pr.state == "merged" else "bold"

        text.append(f"#{pr.number} {pr.title}\n", style=title_style)
        text.append("\n")
        text.append(f"Repo: {pr.repo}\n")
        text.append(f"Author: {display_author_name(pr.author)}\n")

        if pr.state == "merged":
            text.append("State: ")
            text.append("merged\n", style="green")
        else:
            text.append("State: open\n")

        text.append(f"Created: {pr.created_at}\n")
        text.append(f"Updated: {pr.updated_at}\n")

        if pr.merged_at:
            text.append("Merged: ")
            text.append(f"{pr.merged_at}\n", style="green")

        if pr.state == "open":
            idle = days_since(pr.updated_at)
            text.append("PR idle: ")
            text.append(f"{idle}d\n", style=idle_style(idle))

        text.append(f"Review decision: {pr.review_decision or '-'}\n")
        text.append(f"URL: {pr.url}\n")
        text.append("\n")
        text.append("Recent activity:\n", style="bold")

        if not pr.recent_actions:
            text.append("  no recent activity found\n")
        else:
            for action in pr.recent_actions:
                dt = parse_github_datetime(action.created_at).astimezone()
                formatted = dt.strftime("%d.%m %H:%M")
                actor = display_author_name(action.actor)

                text.append(
                    f"  - {formatted} | {action.text} | {actor}\n"
                )

        details.update(text)

    def update_topbar_level_1(self, data: Level1ViewData, from_cache: bool) -> None:
        source = "cache" if from_cache else "fresh"
        inactive_count = data.total_open_prs - data.in_scope_open_prs

        text = (
            f"Level 1 | "
            f"Repos: {data.total_repos} | "
            f"Authors: {data.total_authors} | "
            f"Open total: {data.total_open_prs} | "
            f"Active {LOOKBACK_DAYS}d: {data.in_scope_open_prs} | "
            f"Inactive: {inactive_count} | "
            f"Fetched: {format_fetched_at(data.fetched_at)} | "
            f"Source: {source} | "
            f"Keys: ↑/↓ select, →/Enter=open, r=refresh, q=quit"
        )

        self.query_one("#topbar", Static).update(text)

    def update_topbar_level_2(
        self,
        data: Level2RepoViewData | Level2AuthorViewData,
        from_cache: bool,
    ) -> None:
        source = "cache" if from_cache else "fresh"

        if isinstance(data, Level2RepoViewData):
            target = f"Repo: {data.repo}"
        else:
            target = f"Author: {display_author_name(data.author)}"

        text = (
            f"Level 2 | {target} | "
            f"Open active {LOOKBACK_DAYS}d: {data.open_count} | "
            f"Merged {LOOKBACK_DAYS}d: {data.merged_count} | "
            f"Fetched: {format_fetched_at(data.fetched_at)} | "
            f"Source: {source} | "
            f"Keys: ↑/↓ select, ←/Esc=back, r=refresh, q=quit"
        )

        self.query_one("#topbar", Static).update(text)

    def update_topbar_error(self, error: str) -> None:
        self.query_one("#topbar", Static).update(
            f"Error: {error}"
        )
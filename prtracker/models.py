from dataclasses import dataclass
from datetime import datetime

# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class AuthorSummary:
    author: str
    open_count: int
    active_count: int
    inactive_count: int
    last_activity_days: int | None


@dataclass
class RepoSummary:
    repo: str
    open_total_count: int
    active_count: int
    inactive_count: int
    last_activity_days: int | None
    authors: list[AuthorSummary]


@dataclass
class Level1ViewData:
    repos: list[RepoSummary]
    authors: list[AuthorSummary]
    fetched_at: datetime
    total_open_prs: int
    in_scope_open_prs: int
    total_repos: int
    total_authors: int


@dataclass
class RecentAction:
    created_at: str
    action_type: str
    actor: str
    text: str


@dataclass
class PRSummary:
    repo: str
    number: int
    title: str
    author: str
    state: str
    url: str
    created_at: str
    updated_at: str
    merged_at: str | None
    review_decision: str | None
    recent_actions: list[RecentAction]


@dataclass
class AuthorPRGroup:
    author: str
    open_prs: list[PRSummary]
    merged_prs: list[PRSummary]


@dataclass
class RepoPRGroup:
    repo: str
    open_prs: list[PRSummary]
    merged_prs: list[PRSummary]


@dataclass
class Level2RepoViewData:
    repo: str
    groups: list[AuthorPRGroup]
    fetched_at: datetime
    open_count: int
    merged_count: int


@dataclass
class Level2AuthorViewData:
    author: str
    groups: list[RepoPRGroup]
    fetched_at: datetime
    open_count: int
    merged_count: int

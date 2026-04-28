from datetime import datetime, timezone, timedelta

from prtracker.config import LOOKBACK_DAYS, USER_DISPLAY_NAMES

# ============================================================
# HELPERS
# ============================================================

def display_author_name(github_login: str) -> str:
    return USER_DISPLAY_NAMES.get(github_login, github_login)


def parse_github_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def days_since(date_str: str) -> int:
    dt = parse_github_datetime(date_str)
    now = datetime.now(timezone.utc)
    return (now - dt).days


def format_fetched_at(dt: datetime) -> str:
    return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def lookback_date() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).date().isoformat()


def idle_style(idle_days: int) -> str:
    if idle_days <= 0:
        return "green"
    if idle_days <= 3:
        return "chartreuse3"
    if idle_days <= 6:
        return "yellow"
    if idle_days <= 10:
        return "orange3"
    return "red"
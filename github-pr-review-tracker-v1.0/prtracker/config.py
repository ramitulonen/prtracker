# ============================================================
# CONFIGURATION
# ============================================================

# GitHub organization where the repositories are located.
GITHUB_ORG = "Example"

# GitHub authentication is handled by GitHub CLI.
# Run once before using this tool:
#   gh auth login

# Repositories included in this tool.
# Add/remove repositories here when changing what is monitored.
TRACKED_REPOS = [
    "example1",
    "example2",
    "example3",
]

# How many days back the tool considers PR activity relevant.
LOOKBACK_DAYS = 14

# How many fetched views are kept in memory cache.
MAX_CACHE_ENTRIES = 5

# Optional display names for GitHub users.
# If a login is not listed here, the GitHub login is shown.
USER_DISPLAY_NAMES = {
    # "github_login": "Real Name",
}
PR TRACKER – USAGE GUIDE
========================

DESCRIPTION
-----------
This tool tracks GitHub Pull Requests across selected repositories.
You can view activity by:
- Repository
- Author

Data is fetched using GitHub CLI (gh) and displayed in a terminal UI.


REQUIREMENTS
------------
- Python 3.10+
- GitHub CLI (gh)

Install GitHub CLI:
https://cli.github.com/

Login once:
    gh auth login

Install Python dependencies:
    pip install textual rich


RUNNING THE TOOL
----------------
From project root:

    cd ~/../github-pr-review-tracker
    ./run.sh

OR manually:
    source .venv/bin/activate
    python -m prtracker.main


NAVIGATION
----------
Arrow keys:
    ↑ / ↓   Move selection

Enter / →:
    Open selected item

← / Esc:
    Go back

r:
    Refresh data (clears cache and refetches)

q:
    Quit


LEVEL 1 (MAIN VIEW)
-------------------
Shows:
- Repositories
- Authors

You can:
- Select a repository → see its PRs
- Select an author → see PRs across all repos


LEVEL 2
-------
Repository view:
    PRs grouped by author

Author view:
    PRs grouped by repository

Select PR:
    Shows detailed info on the right


CONFIGURATION
-------------
Edit file:

    prtracker/config.py


TRACKED REPOSITORIES
--------------------
Change which repos are monitored:

    TRACKED_REPOS = [
        "repo1",
        "repo2",
    ]


LOOKBACK WINDOW
---------------
Controls what is considered "active":

    LOOKBACK_DAYS = 14

Example:
- 7  = stricter (only very recent activity)
- 30 = more relaxed


CACHE SIZE
----------
Number of cached views:

    MAX_CACHE_ENTRIES = 5

Cache is cleared when pressing:
    r (refresh)


DISPLAY NAMES (OPTIONAL)
------------------------
You can map GitHub usernames to real names:

    USER_DISPLAY_NAMES = {
        "johndoe": "John Doe",
    }


NOTES
-----
- Data is fetched live from GitHub via GraphQL
- Requires access to the repositories
- GitHub CLI must remain authenticated


KNOWN LIMITATIONS
-----------------
- Max ~100 timeline events per PR (GitHub API limit)
- Level 3 (deep PR interaction) not implemented


TROUBLESHOOTING
---------------
If tool fails:

1. Check GitHub login:
       gh auth status

2. Test GitHub API manually:
       gh api graphql -f query='{ viewer { login } }'

3. Ensure dependencies:
       pip install textual rich

4. If issues persist:
       delete .venv and reinstall


END
---

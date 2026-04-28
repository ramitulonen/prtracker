# prtracker

CLI tool for tracking GitHub pull request activity across repositories and authors using a terminal UI.

---

## Overview

This tool provides a terminal-based interface for monitoring pull request activity across multiple repositories.

You can view:
- Activity per repository
- Activity per author
- Open and recently merged pull requests
- Recent actions (commits, reviews, comments)

Data is fetched using GitHub CLI (`gh`) and displayed using a Textual UI.

---

## Features

- Level 1 view:
  - Repository summary
  - Author summary
- Level 2 view:
  - PRs grouped by author (repo view)
  - PRs grouped by repository (author view)
- Activity filtering based on configurable lookback window
- Recent PR activity timeline
- In-memory caching for faster navigation
- Keyboard-driven navigation

---

## Requirements

- Python 3.10+
- GitHub CLI (`gh`)

Install GitHub CLI:
https://cli.github.com/

Authenticate once:

    gh auth login

---

## Installation

Clone or download the repository.

(Optional) create virtual environment:

    python3 -m venv .venv
    source .venv/bin/activate
    pip install textual rich

---

## Running

From project root:

    ./run.sh

or manually:

    python3 -m prtracker.main

---

## Controls

- ↑ / ↓ → Navigate  
- → / Enter → Open  
- ← / Esc → Back  
- r → Refresh  
- q → Quit  

---

## Configuration

Edit:

    prtracker/config.py

Main settings:

    GITHUB_ORG = "example-org"

    TRACKED_REPOS = [
        "repo1",
        "repo2",
    ]

    LOOKBACK_DAYS = 14
    MAX_CACHE_ENTRIES = 5

Explanation:

- TRACKED_REPOS → which repos are tracked  
- LOOKBACK_DAYS → what counts as "active"  
- MAX_CACHE_ENTRIES → how many views are cached  
- USER_DISPLAY_NAMES → optional nicer names  

---

## How it works

- Uses `gh api graphql`
- Fetches PR data from GitHub
- Builds activity timeline from:
  - commits
  - reviews
  - comments
- Displays everything in a terminal UI

---

## Notes

- No credentials stored in code
- Uses GitHub CLI authentication
- Data is fetched live

---

## Limitations

- No level 3 (deep PR view)
- Limited to 100 PRs per query
- Requires `gh` installed

---

## License

No license specified.

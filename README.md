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
```bash
gh auth login




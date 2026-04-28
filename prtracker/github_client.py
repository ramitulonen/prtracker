import json
import subprocess
from typing import Any

from prtracker.config import GITHUB_ORG
from prtracker.helpers import lookback_date



def run_github_query(query: str) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={query}"],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as e:
        raise RuntimeError(
            "gh CLI ei löydy. Asenna GitHub CLI ja aja ensin: gh auth login"
        ) from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"GitHub-kutsu epäonnistui:\n{e.stderr}") from e

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"GitHub palautti virheellisen JSONin:\n{result.stdout}") from e


def build_repo_query(repo: str) -> str:
    return f"""
    {{
      search(query: "repo:{GITHUB_ORG}/{repo} is:pull-request is:open", type: ISSUE, first: 100) {{
        nodes {{
          ... on PullRequest {{
            number
            title
            createdAt
            updatedAt
            url
            repository {{ name }}
            author {{ login }}
          }}
        }}
      }}
    }}
    """


def build_level_2_query(repo: str) -> str:
    since = lookback_date()

    return f"""
    {{
      openPrs: search(
        query: "repo:{GITHUB_ORG}/{repo} is:pull-request is:open updated:>={since}",
        type: ISSUE,
        first: 100
      ) {{
        nodes {{
          ... on PullRequest {{
            number
            title
            url
            createdAt
            updatedAt
            reviewDecision
            author {{ login }}
            repository {{ name }}

            commits(last: 100) {{
              nodes {{
                commit {{
                  committedDate
                  messageHeadline
                  authors(first: 1) {{
                    nodes {{
                      user {{ login }}
                      name
                    }}
                  }}
                }}
              }}
            }}

            timelineItems(last: 100, itemTypes: [
              REVIEW_REQUESTED_EVENT,
              PULL_REQUEST_REVIEW,
              ISSUE_COMMENT
            ]) {{
              nodes {{
                __typename

                ... on ReviewRequestedEvent {{
                  createdAt
                  actor {{ login }}
                }}

                ... on PullRequestReview {{
                  state
                  createdAt
                  author {{ login }}
                }}

                ... on IssueComment {{
                  createdAt
                  author {{ login }}
                }}
              }}
            }}
          }}
        }}
      }}

      mergedPrs: search(
        query: "repo:{GITHUB_ORG}/{repo} is:pull-request is:merged merged:>={since}",
        type: ISSUE,
        first: 100
      ) {{
        nodes {{
          ... on PullRequest {{
            number
            title
            url
            createdAt
            updatedAt
            mergedAt
            reviewDecision
            author {{ login }}
            repository {{ name }}

            commits(last: 100) {{
              nodes {{
                commit {{
                  committedDate
                  messageHeadline
                  authors(first: 1) {{
                    nodes {{
                      user {{ login }}
                      name
                    }}
                  }}
                }}
              }}
            }}

            timelineItems(last: 100, itemTypes: [
              REVIEW_REQUESTED_EVENT,
              PULL_REQUEST_REVIEW,
              ISSUE_COMMENT
            ]) {{
              nodes {{
                __typename

                ... on ReviewRequestedEvent {{
                  createdAt
                  actor {{ login }}
                }}

                ... on PullRequestReview {{
                  state
                  createdAt
                  author {{ login }}
                }}

                ... on IssueComment {{
                  createdAt
                  author {{ login }}
                }}
              }}
            }}
          }}
        }}
      }}
    }}
    """

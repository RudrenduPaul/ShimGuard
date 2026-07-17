#!/usr/bin/env python3
"""
02 -- CI gate.

Demonstrates using TrackerVerifier as an actual CI gate script: takes a
repo slug and a comma-separated issue list from the command line (falling
back to the real sybil-solutions/codex-shim#45,46 case so it's runnable
with zero arguments), prints a summary, and propagates a real process exit
code -- exactly what you'd drop into a scheduled CI workflow step (see
../../../docs/integrations/ci.md for the GitHub Actions version of this
same pattern).

Run:
    python3 examples/02-ci-gate/gate.py
    python3 examples/02-ci-gate/gate.py octocat/Hello-World 1
"""
import os
import sys

from shimguard import IssueRef, RegexPatternMatcher, RestGitHubClient, TrackerVerifier
from shimguard.cli_lib import format_text, parse_issue_list, parse_repo_slug

DEFAULT_REPO = "sybil-solutions/codex-shim"
DEFAULT_ISSUES = "45,46"


def main() -> int:
    repo_arg = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_REPO
    issues_arg = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_ISSUES

    try:
        owner, repo = parse_repo_slug(repo_arg)
        issue_numbers = parse_issue_list(issues_arg)
    except ValueError as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 2

    client = RestGitHubClient(token=os.environ.get("GITHUB_TOKEN"))
    verifier = TrackerVerifier(client, RegexPatternMatcher(client))

    results = [verifier.verify(IssueRef(owner=owner, repo=repo, number=n)) for n in issue_numbers]

    print(format_text(results, repo_arg))

    if any(r.verdict == "MISMATCH" for r in results):
        print("\nGATE: FAIL -- at least one closed issue's cited fix PR never merged.", file=sys.stderr)
        return 1

    print("\nGATE: PASS -- every checked issue's cited fix is genuinely merged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

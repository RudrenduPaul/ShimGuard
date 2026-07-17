#!/usr/bin/env python3
"""
01 -- basic verify.

The simplest possible use of the shimguard library: build a TrackerVerifier
around a real RestGitHubClient, call verify() for each issue, read back
result.verdict/reason. Runs against the real, currently-live
sybil-solutions/codex-shim#45 and #46 -- the documented real-world case
ShimGuard was built from (see the project README) -- so it needs network
access but no setup beyond `pip install -e .` (or `pip install
shimguard-cli`).

Run:
    python3 examples/01-basic-verify/verify.py
"""
import os

from shimguard import IssueRef, RegexPatternMatcher, RestGitHubClient, TrackerVerifier


def main() -> None:
    # RestGitHubClient does not read $GITHUB_TOKEN automatically (only the
    # CLI does that) -- pass it explicitly to raise the rate limit from
    # 60 to 5,000 requests/hour if it's set in your environment.
    client = RestGitHubClient(token=os.environ.get("GITHUB_TOKEN"))
    verifier = TrackerVerifier(client, RegexPatternMatcher(client))

    for number in (45, 46):
        result = verifier.verify(IssueRef(owner="sybil-solutions", repo="codex-shim", number=number))

        print(f"--- issue #{number} ---")
        print(f"title:   {result.issue.title}")
        print(f"verdict: {result.verdict}")
        if result.cited_pull_request:
            print(
                f"cited fix: PR #{result.cited_pull_request.number} "
                f"(merged={result.cited_pull_request.merged})"
            )
        print(f"reason:  {result.reason}")
        print()


if __name__ == "__main__":
    main()

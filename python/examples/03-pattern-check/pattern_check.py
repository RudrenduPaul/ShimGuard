#!/usr/bin/env python3
"""
03 -- optional code-pattern check.

Demonstrates the --patterns feature: after the merge-state check passes,
TrackerVerifier can also confirm a specific vulnerable code pattern is
actually gone from the file at HEAD, not just that some PR merged.

Part 1 (real, live): points --patterns-equivalent code at the real
sybil-solutions/codex-shim#45 case. Because PR #52 was never merged, the
verdict is already MISMATCH from the merge-state check alone -- the pattern
check never runs (pattern_check stays None), which is itself the correct,
real behavior: ShimGuard doesn't spend an extra API call confirming code
state once the tracker claim is already known to be false.

Part 2 (synthetic, in-memory): a real public repo with a *merged* PR that
still leaves the cited vulnerable pattern in place is not something we have
a handy, stable example of. To show that downgrade path concretely, this
part builds a small in-memory GitHubClient (implementing the same protocol
RestGitHubClient does) with a merged PR and a file that still contains the
cited pattern, and shows TrackerVerifier downgrading MATCH to MISMATCH.

Run:
    python3 examples/03-pattern-check/pattern_check.py
"""
import os
from typing import List, Optional

from shimguard import (
    GitHubComment,
    GitHubIssue,
    GitHubPullRequest,
    IssueRef,
    RegexPatternMatcher,
    RestGitHubClient,
    TrackerVerifier,
)
from shimguard.verifier import PatternSpec


def part1_real_short_circuit() -> None:
    print("=== Part 1: real repo, merge check short-circuits the pattern check ===")
    client = RestGitHubClient(token=os.environ.get("GITHUB_TOKEN"))
    verifier = TrackerVerifier(client, RegexPatternMatcher(client))

    result = verifier.verify(
        IssueRef(owner="sybil-solutions", repo="codex-shim", number=45),
        PatternSpec(path="codex_shim/settings.py", pattern="_resolve_api_key"),
    )
    print(f"verdict:       {result.verdict}")
    print(f"pattern_check: {result.pattern_check}  (None -- never reached, PR was already unmerged)")
    print(f"reason:        {result.reason}")
    print()


class _InMemoryGitHubClient:
    """A minimal GitHubClient for demonstrating the downgrade path without a
    real merged-but-still-vulnerable public example handy."""

    def __init__(self) -> None:
        self._issue = GitHubIssue(
            number=1,
            title="Demo: fallback key leak",
            state="closed",
            body="Some bug.",
            closed_at="2026-01-01T00:00:00Z",
        )
        self._comments = [GitHubComment(body="Fixed in #2", created_at="2026-01-01T00:00:00Z")]
        self._pr = GitHubPullRequest(
            number=2, state="closed", merged=True, merged_at="2026-01-01T00:00:00Z", html_url="https://example.com/pull/2"
        )
        self._files = {"settings.py": "def _resolve_api_key():\n    return cursor_key_fallback()\n"}

    def get_issue(self, owner: str, repo: str, number: int) -> GitHubIssue:
        return self._issue

    def get_issue_comments(self, owner: str, repo: str, number: int) -> List[GitHubComment]:
        return self._comments

    def get_pull_request(self, owner: str, repo: str, number: int) -> GitHubPullRequest:
        return self._pr

    def get_file_content(self, owner: str, repo: str, path: str, ref: str = "HEAD") -> Optional[str]:
        return self._files.get(path)


def part2_synthetic_downgrade() -> None:
    print("=== Part 2: synthetic case, merged PR that left the pattern in place ===")
    client = _InMemoryGitHubClient()
    verifier = TrackerVerifier(client, RegexPatternMatcher(client))

    result = verifier.verify(
        IssueRef(owner="demo", repo="demo", number=1),
        PatternSpec(path="settings.py", pattern="cursor_key_fallback"),
    )
    print(f"verdict:       {result.verdict}  (downgraded from MATCH)")
    print(f"pattern_check: found={result.pattern_check.found}")
    print(f"reason:        {result.reason}")


if __name__ == "__main__":
    part1_real_short_circuit()
    part2_synthetic_downgrade()

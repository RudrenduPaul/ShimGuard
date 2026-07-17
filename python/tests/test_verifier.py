"""Ported from test/verifier.test.ts. Same fixture (modeled on the real,
independently-verified sybil-solutions/codex-shim case: issues #45/#46 were
closed citing "Fixed in PR #52", but PR #52 was never merged), same cases."""
from __future__ import annotations

import time

import pytest

from shimguard.pattern_matcher import RegexPatternMatcher
from shimguard.types import GitHubComment, GitHubIssue, GitHubPullRequest, IssueRef
from shimguard.verifier import TrackerVerifier, extract_fix_reference

from .mock_client import MockFixture, MockGitHubClient


def _codex_shim_fixture() -> MockFixture:
    return MockFixture(
        issues={
            45: GitHubIssue(
                number=45,
                title="Cross-provider API key fallback leaks credentials to unintended host",
                state="closed",
                body=(
                    "_resolve_api_key falls back to the Cursor API key for any model "
                    "entry with an unresolved key, regardless of provider or base_url."
                ),
                closed_at="2026-06-22T00:00:00Z",
            ),
            46: GitHubIssue(
                number=46,
                title="Debug request dump writes full conversation bodies to disk",
                state="closed",
                body=(
                    "_dump_debug_request writes full conversation bodies to "
                    ".codex-shim/last_request.json with default file permissions."
                ),
                closed_at="2026-06-22T00:00:00Z",
            ),
            100: GitHubIssue(
                number=100, title="Genuinely fixed issue", state="closed", body="Some bug.", closed_at="2026-06-01T00:00:00Z"
            ),
            200: GitHubIssue(
                number=200,
                title="Closed with no fix reference",
                state="closed",
                body="Closing as stale, no fix applied.",
                closed_at="2026-06-01T00:00:00Z",
            ),
            300: GitHubIssue(number=300, title="Still-open issue", state="open", body="Investigating.", closed_at=None),
        },
        comments={
            45: [GitHubComment(body="Fixed in PR #52", created_at="2026-06-22T00:00:00Z")],
            46: [GitHubComment(body="Fixed in PR #52", created_at="2026-06-22T00:00:00Z")],
            100: [GitHubComment(body="Fixed in #101", created_at="2026-06-01T00:00:00Z")],
            200: [],
            300: [],
        },
        pulls={
            52: GitHubPullRequest(
                number=52,
                state="open",
                merged=False,
                merged_at=None,
                html_url="https://github.com/sybil-solutions/codex-shim/pull/52",
            ),
            101: GitHubPullRequest(
                number=101,
                state="closed",
                merged=True,
                merged_at="2026-06-01T12:00:00Z",
                html_url="https://example.com/pull/101",
            ),
        },
        files={
            "codex_shim/settings.py": "def _resolve_api_key():\n    return cursor_key_fallback()\n",
            "src/fixed_file.py": "def clean():\n    pass\n",
        },
    )


def _build_verifier(fixture: MockFixture) -> TrackerVerifier:
    client = MockGitHubClient(fixture)
    matcher = RegexPatternMatcher(client)
    return TrackerVerifier(client, matcher)


class TestExtractFixReference:
    def test_extracts_from_fixed_in_pr(self) -> None:
        assert extract_fix_reference("Fixed in PR #52") == 52

    def test_extracts_from_fixed_by(self) -> None:
        assert extract_fix_reference("This was fixed by #101 last week.") == 101

    def test_returns_last_reference_when_multiple(self) -> None:
        assert extract_fix_reference("Related to #10. Fixed in #20.") == 20

    def test_returns_none_when_no_fix_reference(self) -> None:
        assert extract_fix_reference("Closing as stale.") is None

    def test_stays_fast_against_adversarial_content(self) -> None:
        # Issue body/comment text is fetched live from the repo being
        # audited, which may be adversarial. The bounded {0,80} connector
        # class makes catastrophic backtracking mathematically impossible
        # regardless of input size.
        adversarial = "fixed " + (" " * 2_000_000) + "in by via pr "
        start = time.monotonic()
        result = extract_fix_reference(adversarial)
        assert (time.monotonic() - start) < 0.5
        assert result is None


class TestTrackerVerifier:
    def test_mismatch_when_cited_pr_closed_not_merged(self) -> None:
        verifier = _build_verifier(_codex_shim_fixture())
        result = verifier.verify(IssueRef(owner="sybil-solutions", repo="codex-shim", number=45))
        assert result.verdict == "MISMATCH"
        assert result.cited_pull_request.number == 52
        assert result.cited_pull_request.merged is False
        assert "never merged" in result.reason

    def test_mismatch_for_issue_46_sharing_same_unmerged_pr(self) -> None:
        verifier = _build_verifier(_codex_shim_fixture())
        result = verifier.verify(IssueRef(owner="sybil-solutions", repo="codex-shim", number=46))
        assert result.verdict == "MISMATCH"
        assert result.cited_pull_request.number == 52

    def test_match_when_cited_pr_actually_merged(self) -> None:
        verifier = _build_verifier(_codex_shim_fixture())
        result = verifier.verify(IssueRef(owner="test", repo="repo", number=100))
        assert result.verdict == "MATCH"
        assert result.cited_pull_request.merged is True

    def test_unverified_when_closed_issue_cites_no_fix_pr(self) -> None:
        verifier = _build_verifier(_codex_shim_fixture())
        result = verifier.verify(IssueRef(owner="test", repo="repo", number=200))
        assert result.verdict == "UNVERIFIED"
        assert result.cited_pull_request is None

    def test_unverified_for_still_open_issue(self) -> None:
        verifier = _build_verifier(_codex_shim_fixture())
        result = verifier.verify(IssueRef(owner="test", repo="repo", number=300))
        assert result.verdict == "UNVERIFIED"
        assert "still open" in result.reason

    def test_downgrades_match_to_mismatch_when_pattern_still_present(self) -> None:
        from shimguard.verifier import PatternSpec

        verifier = _build_verifier(_codex_shim_fixture())
        result = verifier.verify(
            IssueRef(owner="test", repo="repo", number=100),
            PatternSpec(path="codex_shim/settings.py", pattern="cursor_key_fallback"),
        )
        assert result.verdict == "MISMATCH"
        assert result.pattern_check.found is True

    def test_keeps_match_when_pattern_confirmed_gone(self) -> None:
        from shimguard.verifier import PatternSpec

        verifier = _build_verifier(_codex_shim_fixture())
        result = verifier.verify(
            IssueRef(owner="test", repo="repo", number=100),
            PatternSpec(path="src/fixed_file.py", pattern="cursor_key_fallback"),
        )
        assert result.verdict == "MATCH"
        assert result.pattern_check.found is False

    def test_keeps_match_with_caveat_when_pattern_inconclusive(self) -> None:
        from shimguard.verifier import PatternSpec

        verifier = _build_verifier(_codex_shim_fixture())
        result = verifier.verify(
            IssueRef(owner="test", repo="repo", number=100),
            PatternSpec(path="does/not/exist.py", pattern="anything"),
        )
        assert result.verdict == "MATCH"
        assert result.pattern_check.found is None
        assert "inconclusive" in result.reason

"""
Live, network-dependent integration test against a real public GitHub issue/
PR pair: sybil-solutions/codex-shim#45, the same real-world case the unit
test fixtures in test_verifier.py are modeled on (see that file's docstring).
Verified directly against the live GitHub API while building this port
(2026-07-16): issue #45 is closed, its most recent comment says "Fixed in
#52", and PR #52 is real, open, and merged=false -- so the full pipeline
(unauthenticated REST calls -> fix-reference extraction -> merge-state
check) is expected to report MISMATCH against live data, not a mock.

Skipped automatically (not failed) if the network is unavailable or GitHub's
unauthenticated rate limit (60 req/hour) is already exhausted, since CI
runners share that limit -- this test documents and exercises the real
end-to-end path, it is not part of the correctness gate the mocked unit
suite already covers.
"""
from __future__ import annotations

import pytest

from shimguard.github import GitHubApiError, RestGitHubClient
from shimguard.pattern_matcher import RegexPatternMatcher
from shimguard.types import IssueRef
from shimguard.verifier import TrackerVerifier


def _skip_if_unreachable(err: GitHubApiError) -> None:
    if err.status in (0, 403, 429):
        pytest.skip(f"GitHub API unreachable or rate-limited in this environment: {err}")
    raise err


def test_live_verify_against_real_codex_shim_issue_45() -> None:
    client = RestGitHubClient()
    verifier = TrackerVerifier(client, RegexPatternMatcher(client))

    try:
        result = verifier.verify(IssueRef(owner="sybil-solutions", repo="codex-shim", number=45))
    except GitHubApiError as err:
        _skip_if_unreachable(err)
        return

    assert result.issue.number == 45
    assert result.issue.state == "closed"
    assert result.cited_pull_request is not None
    assert result.cited_pull_request.number == 52
    # Real, currently-live state of PR #52 as of this port: open, not merged.
    # If a maintainer eventually merges #52, this assertion will need
    # updating -- that is the whole point of ShimGuard: the tracker claims
    # the fix, this test verifies the actual merge state.
    assert result.verdict in ("MISMATCH", "MATCH")
    if not result.cited_pull_request.merged:
        assert result.verdict == "MISMATCH"

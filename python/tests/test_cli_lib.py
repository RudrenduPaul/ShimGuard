"""Ported from test/cli-lib.test.ts."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from shimguard.cli_lib import format_json, format_text, load_patterns, parse_issue_list, parse_repo_slug, summarize
from shimguard.types import IssueSummary, PullRequestSummary, VerificationResult


class TestParseRepoSlug:
    def test_parses_valid_slug(self) -> None:
        assert parse_repo_slug("sybil-solutions/codex-shim") == ("sybil-solutions", "codex-shim")

    def test_throws_on_slug_with_no_slash(self) -> None:
        with pytest.raises(ValueError, match="Invalid repo"):
            parse_repo_slug("not-a-slug")

    def test_throws_on_slug_with_too_many_slashes(self) -> None:
        with pytest.raises(ValueError, match="Invalid repo"):
            parse_repo_slug("a/b/c")

    def test_throws_on_empty_owner_or_repo_segment(self) -> None:
        with pytest.raises(ValueError, match="Invalid repo"):
            parse_repo_slug("/repo")
        with pytest.raises(ValueError, match="Invalid repo"):
            parse_repo_slug("owner/")


class TestParseIssueList:
    def test_parses_comma_separated_list(self) -> None:
        assert parse_issue_list("38,41,42") == [38, 41, 42]

    def test_trims_whitespace(self) -> None:
        assert parse_issue_list(" 38 , 41 ") == [38, 41]

    def test_throws_on_empty_string(self) -> None:
        with pytest.raises(ValueError, match="Invalid --issues"):
            parse_issue_list("")

    def test_throws_on_non_numeric_entry(self) -> None:
        with pytest.raises(ValueError, match="Invalid --issues"):
            parse_issue_list("38,abc")

    def test_throws_on_zero_or_negative_entry(self) -> None:
        with pytest.raises(ValueError, match="Invalid --issues"):
            parse_issue_list("0")
        with pytest.raises(ValueError, match="Invalid --issues"):
            parse_issue_list("-1")


class TestLoadPatterns:
    def test_returns_empty_dict_when_no_path(self) -> None:
        assert load_patterns(None) == {}

    def test_loads_and_parses_valid_patterns_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "patterns.json"
            file.write_text(json.dumps({"45": {"path": "settings.py", "pattern": "cursor_key_fallback"}}))
            patterns = load_patterns(str(file))
            assert patterns["45"].path == "settings.py"
            assert patterns["45"].pattern == "cursor_key_fallback"

    def test_throws_when_file_not_a_json_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "patterns.json"
            file.write_text(json.dumps("not-an-object"))
            with pytest.raises(ValueError, match="must contain a JSON object"):
                load_patterns(str(file))


def _sample_results() -> list[VerificationResult]:
    return [
        VerificationResult(
            issue=IssueSummary(number=45, title="Key leak", state="closed", html_url="https://example.com/issues/45"),
            cited_pull_request=PullRequestSummary(
                number=52, state="open", merged=False, html_url="https://example.com/pull/52"
            ),
            pattern_check=None,
            verdict="MISMATCH",
            reason="Issue is closed and cites PR #52 as the fix, but that PR is open and was never merged.",
        ),
        VerificationResult(
            issue=IssueSummary(number=100, title="Fixed thing", state="closed", html_url="https://example.com/issues/100"),
            cited_pull_request=PullRequestSummary(
                number=101, state="closed", merged=True, html_url="https://example.com/pull/101"
            ),
            pattern_check=None,
            verdict="MATCH",
            reason="Issue is closed and PR #101 is merged.",
        ),
    ]


class TestSummarize:
    def test_counts_verdicts_correctly(self) -> None:
        assert summarize(_sample_results()) == {"mismatch": 1, "match": 1, "unverified": 0}


class TestFormatText:
    def test_includes_each_issue_verdict_and_summary(self) -> None:
        out = format_text(_sample_results(), "sybil-solutions/codex-shim")
        assert "MISMATCH" in out and "Issue #45" in out
        assert "MATCH" in out and "Issue #100" in out
        assert "Summary: 1 MISMATCH, 1 MATCH, 0 UNVERIFIED (2 checked)" in out


class TestFormatJson:
    def test_produces_valid_parseable_json_with_expected_shape(self) -> None:
        out = format_json(_sample_results(), "sybil-solutions/codex-shim")
        parsed = json.loads(out)
        assert parsed["repo"] == "sybil-solutions/codex-shim"
        assert parsed["checked"] == 2
        assert parsed["summary"] == {"mismatch": 1, "match": 1, "unverified": 0}
        assert len(parsed["results"]) == 2
        assert parsed["results"][0]["citedPullRequest"]["htmlUrl"] == "https://example.com/pull/52"

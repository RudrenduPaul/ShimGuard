"""Ported from test/pattern-matcher.test.ts."""
from __future__ import annotations

import time

from shimguard.pattern_matcher import RegexPatternMatcher

from .mock_client import MockFixture, MockGitHubClient


def _base_fixture() -> MockFixture:
    return MockFixture(
        files={
            "clean.py": "def clean():\n    pass\n",
            "vulnerable.py": "def leak():\n    return cursor_key_fallback()\n",
            # 35 'a' characters is enough to trigger catastrophic backtracking
            # against (\w+\s*)+$, confirmed with a standalone reproduction
            # (same bait string the TS test suite uses).
            "redos-bait.py": ("a" * 35) + "!",
            "huge.py": "x" * 1_100_000,
        }
    )


def _build_matcher(fixture: MockFixture) -> RegexPatternMatcher:
    return RegexPatternMatcher(MockGitHubClient(fixture))


class TestRegexPatternMatcherCheck:
    def test_found_true_when_pattern_matches(self) -> None:
        matcher = _build_matcher(_base_fixture())
        result = matcher.check("o", "r", "vulnerable.py", "cursor_key_fallback")
        assert result.found is True

    def test_found_false_when_pattern_does_not_match(self) -> None:
        matcher = _build_matcher(_base_fixture())
        result = matcher.check("o", "r", "clean.py", "cursor_key_fallback")
        assert result.found is False

    def test_found_none_when_file_missing(self) -> None:
        matcher = _build_matcher(_base_fixture())
        result = matcher.check("o", "r", "missing.py", "anything")
        assert result.found is None
        assert "not found" in result.note

    def test_found_none_for_invalid_regex(self) -> None:
        matcher = _build_matcher(_base_fixture())
        result = matcher.check("o", "r", "clean.py", "(unclosed")
        assert result.found is None
        assert "Invalid pattern regex" in result.note

    def test_skips_matching_when_content_exceeds_size_cap(self) -> None:
        matcher = _build_matcher(_base_fixture())
        result = matcher.check("o", "r", "huge.py", "x+")
        assert result.found is None
        assert "larger than" in result.note

    def test_aborts_on_catastrophic_backtracking(self) -> None:
        matcher = _build_matcher(_base_fixture())
        start = time.monotonic()
        result = matcher.check("o", "r", "redos-bait.py", r"(\w+\s*)+$")
        elapsed = time.monotonic() - start
        assert result.found is None
        assert "exceeded" in result.note and "aborted" in result.note
        # The subprocess has a 2s deadline; the whole check must return well
        # under the time an unguarded catastrophic backtrack would actually
        # take.
        assert elapsed < 6.0

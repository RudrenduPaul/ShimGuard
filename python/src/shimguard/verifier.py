"""
Ported from src/verifier.ts (TrackerVerifier, extractFixReference). Same
core, unambiguous check: tracker state (closed, cites a fix PR) vs. actual
PR merge state. Same optional secondary check via a PatternMatcher for
whether the cited vulnerable code pattern is still present at HEAD.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from .pattern_matcher import PatternMatcher
from .types import (
    GitHubClient,
    IssueRef,
    IssueSummary,
    PullRequestSummary,
    VerificationResult,
)

# Matched against issue body/comment text fetched live from the repo being
# audited, which may be adversarial. The connector text between the keyword
# and "#N" is bounded to 80 chars via a single non-backtracking character
# class instead of chained optional/greedy groups -- the same ReDoS-safe
# shape as src/verifier.ts's FIX_REFERENCE_PATTERN, ported verbatim.
FIX_REFERENCE_PATTERN = re.compile(
    r"\b(?:fixed|resolved|closed|addressed)\b[^#\n]{0,80}#(\d+)", re.IGNORECASE
)


def extract_fix_reference(text: str) -> Optional[int]:
    """
    Extracts the PR number a piece of text claims fixed an issue, e.g.
    "Fixed in PR #52", "fixed by #52", "resolved in #52". Returns the last
    match found (closing comments are usually the most authoritative and
    tend to come after earlier discussion in the same body/thread).
    """
    matches: List["re.Match[str]"] = list(FIX_REFERENCE_PATTERN.finditer(text))
    if not matches:
        return None
    raw = matches[-1].group(1)
    try:
        return int(raw)
    except ValueError:
        return None


@dataclass(frozen=True)
class PatternSpec:
    path: str
    pattern: str


class TrackerVerifier:
    def __init__(self, client: GitHubClient, pattern_matcher: Optional[PatternMatcher] = None) -> None:
        self.client = client
        self.pattern_matcher = pattern_matcher

    def verify(self, ref: IssueRef, pattern_spec: Optional[PatternSpec] = None) -> VerificationResult:
        issue = self.client.get_issue(ref.owner, ref.repo, ref.number)
        issue_url = f"https://github.com/{ref.owner}/{ref.repo}/issues/{ref.number}"
        issue_summary = IssueSummary(
            number=issue.number, title=issue.title, state=issue.state, html_url=issue_url
        )

        if issue.state == "open":
            return VerificationResult(
                issue=issue_summary,
                cited_pull_request=None,
                pattern_check=None,
                verdict="UNVERIFIED",
                reason="Issue is still open; no fix has been claimed.",
            )

        comments = self.client.get_issue_comments(ref.owner, ref.repo, ref.number)
        search_text = "\n".join([issue.body or ""] + [c.body for c in comments])
        pr_number = extract_fix_reference(search_text)

        if pr_number is None:
            return VerificationResult(
                issue=issue_summary,
                cited_pull_request=None,
                pattern_check=None,
                verdict="UNVERIFIED",
                reason=(
                    'Issue is closed but no fix PR reference (e.g. "Fixed in #N") '
                    "was found in its body or comments."
                ),
            )

        pr = self.client.get_pull_request(ref.owner, ref.repo, pr_number)
        cited_pull_request = PullRequestSummary(
            number=pr.number, state=pr.state, merged=pr.merged, html_url=pr.html_url
        )

        if not pr.merged:
            return VerificationResult(
                issue=issue_summary,
                cited_pull_request=cited_pull_request,
                pattern_check=None,
                verdict="MISMATCH",
                reason=(
                    f"Issue is closed and cites PR #{pr_number} as the fix, but that PR "
                    f"is {pr.state} and was never merged."
                ),
            )

        if pattern_spec is None or self.pattern_matcher is None:
            return VerificationResult(
                issue=issue_summary,
                cited_pull_request=cited_pull_request,
                pattern_check=None,
                verdict="MATCH",
                reason=f"Issue is closed and PR #{pr_number} is merged.",
            )

        pattern_check = self.pattern_matcher.check(
            ref.owner, ref.repo, pattern_spec.path, pattern_spec.pattern
        )

        if pattern_check.found is True:
            return VerificationResult(
                issue=issue_summary,
                cited_pull_request=cited_pull_request,
                pattern_check=pattern_check,
                verdict="MISMATCH",
                reason=(
                    f"PR #{pr_number} is merged, but the cited vulnerable pattern is "
                    f"still present in {pattern_spec.path} at HEAD."
                ),
            )

        if pattern_check.found is None:
            return VerificationResult(
                issue=issue_summary,
                cited_pull_request=cited_pull_request,
                pattern_check=pattern_check,
                verdict="MATCH",
                reason=(
                    f"Issue is closed and PR #{pr_number} is merged. Pattern check "
                    f"inconclusive: {pattern_check.note or 'unknown'}."
                ),
            )

        return VerificationResult(
            issue=issue_summary,
            cited_pull_request=cited_pull_request,
            pattern_check=pattern_check,
            verdict="MATCH",
            reason=(
                f"Issue is closed, PR #{pr_number} is merged, and the cited pattern is "
                f"confirmed absent from {pattern_spec.path} at HEAD."
            ),
        )

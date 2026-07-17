"""
Shared data types for ShimGuard's Python port. Mirrors src/types.ts field for
field; the one deliberate adaptation is that every GitHubClient method takes
`owner`, `repo`, and `number`/`path` directly instead of the TypeScript
version's mix of a packed `IssueRef` object (for issue calls) and separate
positional args (for PR/file calls) -- more idiomatic Python, same behavior.
`IssueRef` is kept as the small dataclass `TrackerVerifier.verify()` accepts,
matching the original call shape at that one call site.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Optional, Protocol, runtime_checkable

Verdict = Literal["MATCH", "MISMATCH", "UNVERIFIED"]


@dataclass(frozen=True)
class IssueRef:
    owner: str
    repo: str
    number: int


@dataclass(frozen=True)
class GitHubIssue:
    number: int
    title: str
    state: Literal["open", "closed"]
    body: Optional[str]
    closed_at: Optional[str]


@dataclass(frozen=True)
class GitHubComment:
    body: str
    created_at: str


@dataclass(frozen=True)
class GitHubPullRequest:
    number: int
    state: Literal["open", "closed"]
    merged: bool
    merged_at: Optional[str]
    html_url: str


@dataclass(frozen=True)
class PatternCheck:
    """Path to the file expected to no longer contain the vulnerable pattern,
    the regex source (no flags) matched against its raw content at HEAD, and
    whether it was found -- `None` if the file/check could not run, with
    `note` explaining why (file missing, fetch error, timeout, etc)."""

    path: str
    pattern: str
    found: Optional[bool]
    note: Optional[str] = None


@dataclass(frozen=True)
class IssueSummary:
    number: int
    title: str
    state: str
    html_url: str


@dataclass(frozen=True)
class PullRequestSummary:
    number: int
    state: str
    merged: bool
    html_url: str


@dataclass(frozen=True)
class VerificationResult:
    issue: IssueSummary
    cited_pull_request: Optional[PullRequestSummary]
    pattern_check: Optional[PatternCheck]
    verdict: Verdict
    reason: str


@runtime_checkable
class GitHubClient(Protocol):
    def get_issue(self, owner: str, repo: str, number: int) -> GitHubIssue: ...

    def get_issue_comments(self, owner: str, repo: str, number: int) -> List[GitHubComment]: ...

    def get_pull_request(self, owner: str, repo: str, number: int) -> GitHubPullRequest: ...

    def get_file_content(
        self, owner: str, repo: str, path: str, ref: str = "HEAD"
    ) -> Optional[str]: ...

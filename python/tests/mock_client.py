"""Ported from test/mock-client.ts: an in-memory GitHubClient implementation
for unit-testing TrackerVerifier and RegexPatternMatcher without any real
network call."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from shimguard.types import GitHubComment, GitHubIssue, GitHubPullRequest


@dataclass
class MockFixture:
    issues: Dict[int, GitHubIssue] = field(default_factory=dict)
    comments: Dict[int, List[GitHubComment]] = field(default_factory=dict)
    pulls: Dict[int, GitHubPullRequest] = field(default_factory=dict)
    files: Dict[str, str] = field(default_factory=dict)


class MockGitHubClient:
    def __init__(self, fixture: MockFixture) -> None:
        self.fixture = fixture

    def get_issue(self, owner: str, repo: str, number: int) -> GitHubIssue:
        issue = self.fixture.issues.get(number)
        if issue is None:
            raise AssertionError(f"fixture missing issue #{number}")
        return issue

    def get_issue_comments(self, owner: str, repo: str, number: int) -> List[GitHubComment]:
        return self.fixture.comments.get(number, [])

    def get_pull_request(self, owner: str, repo: str, number: int) -> GitHubPullRequest:
        pr = self.fixture.pulls.get(number)
        if pr is None:
            raise AssertionError(f"fixture missing PR #{number}")
        return pr

    def get_file_content(self, owner: str, repo: str, path: str, ref: str = "HEAD") -> Optional[str]:
        return self.fixture.files.get(path)

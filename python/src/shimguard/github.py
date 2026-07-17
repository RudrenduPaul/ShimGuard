"""
Real GitHub REST API client. Ported from src/github.ts (RestGitHubClient):
same three endpoints (issue, issue comments, pull request), same 404/403/429
handling, same base64-decoded file-content fetch via the contents API. Uses
`requests` in place of the built-in `fetch` the TypeScript version relies on.
"""
from __future__ import annotations

import base64
from typing import List, Optional
from urllib.parse import quote

import requests

from .types import GitHubComment, GitHubIssue, GitHubPullRequest

API_BASE = "https://api.github.com"
TIMEOUT_SECONDS = 15
USER_AGENT = "shimguard-cli"


class GitHubApiError(Exception):
    def __init__(self, message: str, status: int, url: str) -> None:
        super().__init__(message)
        self.status = status
        self.url = url


class RestGitHubClient:
    def __init__(self, token: Optional[str] = None) -> None:
        self.token = token

    def _headers(self) -> dict:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": USER_AGENT,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(self, path: str) -> dict:
        url = f"{API_BASE}{path}"
        try:
            res = requests.get(url, headers=self._headers(), timeout=TIMEOUT_SECONDS)
        except requests.RequestException as err:
            raise GitHubApiError(f"GitHub API request failed for {url}: {err}", 0, url) from err

        if res.status_code in (403, 429):
            remaining = res.headers.get("x-ratelimit-remaining")
            if remaining == "0":
                raise GitHubApiError(
                    "GitHub API rate limit exceeded. Set GITHUB_TOKEN (or --token) to raise the limit.",
                    res.status_code,
                    url,
                )
            raise GitHubApiError(
                f"GitHub API request forbidden ({res.status_code}) for {url}", res.status_code, url
            )
        if res.status_code == 404:
            raise GitHubApiError(f"Not found: {url}", 404, url)
        if not res.ok:
            raise GitHubApiError(
                f"GitHub API request failed ({res.status_code}) for {url}", res.status_code, url
            )
        return res.json()

    def get_issue(self, owner: str, repo: str, number: int) -> GitHubIssue:
        data = self._request(f"/repos/{owner}/{repo}/issues/{number}")
        return GitHubIssue(
            number=data["number"],
            title=data["title"],
            state=data["state"],
            body=data.get("body"),
            closed_at=data.get("closed_at"),
        )

    def get_issue_comments(self, owner: str, repo: str, number: int) -> List[GitHubComment]:
        data = self._request(f"/repos/{owner}/{repo}/issues/{number}/comments?per_page=100")
        return [GitHubComment(body=c["body"], created_at=c["created_at"]) for c in data]

    def get_pull_request(self, owner: str, repo: str, number: int) -> GitHubPullRequest:
        data = self._request(f"/repos/{owner}/{repo}/pulls/{number}")
        return GitHubPullRequest(
            number=data["number"],
            state=data["state"],
            merged=data["merged"],
            merged_at=data.get("merged_at"),
            html_url=data["html_url"],
        )

    def get_file_content(
        self, owner: str, repo: str, path: str, ref: str = "HEAD"
    ) -> Optional[str]:
        try:
            data = self._request(f"/repos/{owner}/{repo}/contents/{path}?ref={quote(ref, safe='')}")
        except GitHubApiError as err:
            if err.status == 404:
                return None
            raise
        if data.get("encoding") != "base64":
            return None
        return base64.b64decode(data["content"]).decode("utf-8")

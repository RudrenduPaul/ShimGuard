"""Unit tests for RestGitHubClient against a mocked HTTP layer (`responses`),
so these run offline and deterministically -- no TS equivalent exists since
src/github.test.ts talks to the real network in one integration-style test;
this port covers the same request/response contract without a live call in
the unit suite. A separate, explicitly-marked live test exists in
test_live_github.py."""
from __future__ import annotations

import base64

import pytest
import responses

from shimguard.github import GitHubApiError, RestGitHubClient


@responses.activate
def test_get_issue_parses_response() -> None:
    responses.add(
        responses.GET,
        "https://api.github.com/repos/o/r/issues/45",
        json={"number": 45, "title": "Some bug", "state": "closed", "body": "text", "closed_at": "2026-01-01T00:00:00Z"},
        status=200,
    )
    client = RestGitHubClient()
    issue = client.get_issue("o", "r", 45)
    assert issue.number == 45
    assert issue.state == "closed"
    assert issue.closed_at == "2026-01-01T00:00:00Z"


@responses.activate
def test_get_issue_comments_parses_response() -> None:
    responses.add(
        responses.GET,
        "https://api.github.com/repos/o/r/issues/45/comments",
        json=[{"body": "Fixed in #52", "created_at": "2026-01-01T00:00:00Z"}],
        status=200,
    )
    client = RestGitHubClient()
    comments = client.get_issue_comments("o", "r", 45)
    assert len(comments) == 1
    assert comments[0].body == "Fixed in #52"


@responses.activate
def test_get_pull_request_parses_response() -> None:
    responses.add(
        responses.GET,
        "https://api.github.com/repos/o/r/pulls/52",
        json={"number": 52, "state": "open", "merged": False, "merged_at": None, "html_url": "https://x/pull/52"},
        status=200,
    )
    client = RestGitHubClient()
    pr = client.get_pull_request("o", "r", 52)
    assert pr.merged is False
    assert pr.html_url == "https://x/pull/52"


@responses.activate
def test_get_file_content_decodes_base64() -> None:
    encoded = base64.b64encode(b"print('hi')\n").decode("ascii")
    responses.add(
        responses.GET,
        "https://api.github.com/repos/o/r/contents/x.py",
        json={"content": encoded, "encoding": "base64"},
        status=200,
    )
    client = RestGitHubClient()
    content = client.get_file_content("o", "r", "x.py")
    assert content == "print('hi')\n"


@responses.activate
def test_get_file_content_returns_none_on_404() -> None:
    responses.add(
        responses.GET,
        "https://api.github.com/repos/o/r/contents/missing.py",
        json={"message": "Not Found"},
        status=404,
    )
    client = RestGitHubClient()
    assert client.get_file_content("o", "r", "missing.py") is None


def test_get_file_content_rejects_dot_dot_path_traversal() -> None:
    client = RestGitHubClient()
    with pytest.raises(ValueError, match="must be a relative path"):
        client.get_file_content("o", "r", "../../../other-owner/other-repo/contents/secret.txt")


def test_get_file_content_rejects_bare_dot_segment() -> None:
    client = RestGitHubClient()
    with pytest.raises(ValueError, match="must be a relative path"):
        client.get_file_content("o", "r", "src/./config.py")


@responses.activate
def test_get_file_content_allows_ordinary_nested_path() -> None:
    encoded = base64.b64encode(b"x = 1\n").decode("ascii")
    responses.add(
        responses.GET,
        "https://api.github.com/repos/o/r/contents/src/config.py",
        json={"content": encoded, "encoding": "base64"},
        status=200,
    )
    client = RestGitHubClient()
    assert client.get_file_content("o", "r", "src/config.py") == "x = 1\n"


@responses.activate
def test_raises_not_found_for_404_issue() -> None:
    responses.add(
        responses.GET,
        "https://api.github.com/repos/o/r/issues/999",
        json={"message": "Not Found"},
        status=404,
    )
    client = RestGitHubClient()
    with pytest.raises(GitHubApiError) as exc_info:
        client.get_issue("o", "r", 999)
    assert exc_info.value.status == 404


@responses.activate
def test_raises_rate_limit_error_when_remaining_is_zero() -> None:
    responses.add(
        responses.GET,
        "https://api.github.com/repos/o/r/issues/1",
        json={"message": "rate limited"},
        status=403,
        headers={"x-ratelimit-remaining": "0"},
    )
    client = RestGitHubClient()
    with pytest.raises(GitHubApiError, match="rate limit exceeded"):
        client.get_issue("o", "r", 1)


@responses.activate
def test_sends_bearer_token_when_provided() -> None:
    responses.add(
        responses.GET,
        "https://api.github.com/repos/o/r/issues/1",
        json={"number": 1, "title": "t", "state": "open", "body": None, "closed_at": None},
        status=200,
    )
    client = RestGitHubClient(token="secret-token")
    client.get_issue("o", "r", 1)
    assert responses.calls[0].request.headers["Authorization"] == "Bearer secret-token"

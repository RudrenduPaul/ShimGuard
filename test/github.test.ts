import { afterEach, describe, expect, it, vi } from "vitest";
import { RestGitHubClient, GitHubApiError } from "../src/github.js";

function jsonResponse(body: unknown, status = 200, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), { status, headers });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("RestGitHubClient.getIssue", () => {
  it("maps the GitHub API issue shape to our GitHubIssue type", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        number: 45,
        title: "Key leak",
        state: "closed",
        body: "body text",
        closed_at: "2026-06-22T00:00:00Z",
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const client = new RestGitHubClient();
    const issue = await client.getIssue({ owner: "o", repo: "r", number: 45 });

    expect(issue).toEqual({
      number: 45,
      title: "Key leak",
      state: "closed",
      body: "body text",
      closedAt: "2026-06-22T00:00:00Z",
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.github.com/repos/o/r/issues/45",
      expect.objectContaining({ headers: expect.objectContaining({ "User-Agent": "shimguard-cli" }) }),
    );
  });

  it("sends an Authorization header when a token is provided", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ number: 1, title: "t", state: "open", body: null, closed_at: null }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const client = new RestGitHubClient("my-token");
    await client.getIssue({ owner: "o", repo: "r", number: 1 });

    expect(fetchMock).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: "Bearer my-token" }) }),
    );
  });

  it("throws GitHubApiError with status 404 for a missing issue", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({}, 404)));
    const client = new RestGitHubClient();
    await expect(client.getIssue({ owner: "o", repo: "r", number: 999 })).rejects.toThrow(GitHubApiError);
  });

  it("throws a clear rate-limit error when x-ratelimit-remaining is 0", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({}, 403, { "x-ratelimit-remaining": "0" })),
    );
    const client = new RestGitHubClient();
    await expect(client.getIssue({ owner: "o", repo: "r", number: 1 })).rejects.toThrow(/rate limit exceeded/);
  });
});

describe("RestGitHubClient.getPullRequest", () => {
  it("maps merged_at/html_url correctly", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({
          number: 52,
          state: "open",
          merged: false,
          merged_at: null,
          html_url: "https://github.com/o/r/pull/52",
        }),
      ),
    );
    const client = new RestGitHubClient();
    const pr = await client.getPullRequest("o", "r", 52);
    expect(pr).toEqual({
      number: 52,
      state: "open",
      merged: false,
      mergedAt: null,
      htmlUrl: "https://github.com/o/r/pull/52",
    });
  });
});

describe("RestGitHubClient.getIssueComments", () => {
  it("maps comment bodies and timestamps", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse([{ body: "Fixed in PR #52", created_at: "2026-06-22T00:00:00Z" }]),
      ),
    );
    const client = new RestGitHubClient();
    const comments = await client.getIssueComments({ owner: "o", repo: "r", number: 45 });
    expect(comments).toEqual([{ body: "Fixed in PR #52", createdAt: "2026-06-22T00:00:00Z" }]);
  });
});

describe("RestGitHubClient.getFileContent", () => {
  it("decodes base64 file content", async () => {
    const content = "def foo():\n    pass\n";
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({ content: Buffer.from(content, "utf-8").toString("base64"), encoding: "base64" }),
      ),
    );
    const client = new RestGitHubClient();
    const result = await client.getFileContent("o", "r", "settings.py");
    expect(result).toBe(content);
  });

  it("returns null for a 404 (file not found)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({}, 404)));
    const client = new RestGitHubClient();
    const result = await client.getFileContent("o", "r", "missing.py");
    expect(result).toBeNull();
  });

  it("returns null when the response encoding is not base64", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ content: "", encoding: "none" })));
    const client = new RestGitHubClient();
    const result = await client.getFileContent("o", "r", "weird.bin");
    expect(result).toBeNull();
  });

  it("rejects a path containing a '..' segment instead of requesting it", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const client = new RestGitHubClient();
    await expect(
      client.getFileContent("o", "r", "../../../other-owner/other-repo/contents/secret.txt"),
    ).rejects.toThrow(/must be a relative path/);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects a path containing a bare '.' segment", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const client = new RestGitHubClient();
    await expect(client.getFileContent("o", "r", "src/./config.py")).rejects.toThrow(/must be a relative path/);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("still allows an ordinary nested path", async () => {
    const content = "x = 1\n";
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({ content: Buffer.from(content, "utf-8").toString("base64"), encoding: "base64" }),
      ),
    );
    const client = new RestGitHubClient();
    const result = await client.getFileContent("o", "r", "src/config.py");
    expect(result).toBe(content);
  });
});

import type { GitHubClient, GitHubComment, GitHubIssue, GitHubPullRequest } from "./types.js";

const API_BASE = "https://api.github.com";

/**
 * Encodes a repo-relative file path for use in a GitHub Contents API URL,
 * rejecting ".."/"." segments so a `--patterns` file supplied by (or
 * copied from) the repo being audited cannot redirect the request to a
 * different repo or API endpoint via path traversal.
 */
function encodeRepoPath(rawPath: string): string {
  const segments = rawPath.split("/");
  if (segments.length === 0 || segments.some((s) => s.length === 0 || s === "." || s === "..")) {
    throw new Error(
      `Invalid file path "${rawPath}": must be a relative path with no empty, "." or ".." segments.`,
    );
  }
  return segments.map((s) => encodeURIComponent(s)).join("/");
}

export class GitHubApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly url: string,
  ) {
    super(message);
    this.name = "GitHubApiError";
  }
}

export class RestGitHubClient implements GitHubClient {
  constructor(private readonly token?: string) {}

  private async request<T>(path: string): Promise<T> {
    const url = `${API_BASE}${path}`;
    const headers: Record<string, string> = {
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "shimguard-cli",
    };
    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }

    const res = await fetch(url, { headers, signal: AbortSignal.timeout(15_000) });
    if (res.status === 403 || res.status === 429) {
      const remaining = res.headers.get("x-ratelimit-remaining");
      throw new GitHubApiError(
        remaining === "0"
          ? "GitHub API rate limit exceeded. Set GITHUB_TOKEN (or --token) to raise the limit."
          : `GitHub API request forbidden (${res.status}) for ${url}`,
        res.status,
        url,
      );
    }
    if (res.status === 404) {
      throw new GitHubApiError(`Not found: ${url}`, 404, url);
    }
    if (!res.ok) {
      throw new GitHubApiError(`GitHub API request failed (${res.status}) for ${url}`, res.status, url);
    }
    return (await res.json()) as T;
  }

  async getIssue(ref: { owner: string; repo: string; number: number }): Promise<GitHubIssue> {
    const data = await this.request<{
      number: number;
      title: string;
      state: "open" | "closed";
      body: string | null;
      closed_at: string | null;
      pull_request?: unknown;
    }>(`/repos/${encodeURIComponent(ref.owner)}/${encodeURIComponent(ref.repo)}/issues/${ref.number}`);
    return {
      number: data.number,
      title: data.title,
      state: data.state,
      body: data.body,
      closedAt: data.closed_at,
    };
  }

  async getIssueComments(ref: { owner: string; repo: string; number: number }): Promise<GitHubComment[]> {
    const data = await this.request<Array<{ body: string; created_at: string }>>(
      `/repos/${encodeURIComponent(ref.owner)}/${encodeURIComponent(ref.repo)}/issues/${ref.number}/comments?per_page=100`,
    );
    return data.map((c) => ({ body: c.body, createdAt: c.created_at }));
  }

  async getPullRequest(owner: string, repo: string, number: number): Promise<GitHubPullRequest> {
    const data = await this.request<{
      number: number;
      state: "open" | "closed";
      merged: boolean;
      merged_at: string | null;
      html_url: string;
    }>(`/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/pulls/${number}`);
    return {
      number: data.number,
      state: data.state,
      merged: data.merged,
      mergedAt: data.merged_at,
      htmlUrl: data.html_url,
    };
  }

  async getFileContent(owner: string, repo: string, path: string, ref = "HEAD"): Promise<string | null> {
    const safePath = encodeRepoPath(path);
    try {
      const data = await this.request<{ content: string; encoding: string }>(
        `/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/contents/${safePath}?ref=${encodeURIComponent(ref)}`,
      );
      if (data.encoding !== "base64") {
        return null;
      }
      return Buffer.from(data.content, "base64").toString("utf-8");
    } catch (err) {
      if (err instanceof GitHubApiError && err.status === 404) {
        return null;
      }
      throw err;
    }
  }
}

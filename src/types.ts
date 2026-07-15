export type Verdict = "MATCH" | "MISMATCH" | "UNVERIFIED";

export interface IssueRef {
  owner: string;
  repo: string;
  number: number;
}

export interface GitHubIssue {
  number: number;
  title: string;
  state: "open" | "closed";
  body: string | null;
  closedAt: string | null;
}

export interface GitHubComment {
  body: string;
  createdAt: string;
}

export interface GitHubPullRequest {
  number: number;
  state: "open" | "closed";
  merged: boolean;
  mergedAt: string | null;
  htmlUrl: string;
}

export interface PatternCheck {
  /** Path to the file expected to no longer contain the vulnerable pattern. */
  path: string;
  /** Regex source (no flags) matched against the file's raw content. */
  pattern: string;
  /** Whether the pattern was found at HEAD. Absent if the file/check could not run. */
  found: boolean | null;
  /** Human-readable reason when `found` is null (file missing, fetch error, etc). */
  note?: string;
}

export interface VerificationResult {
  issue: {
    number: number;
    title: string;
    state: "open" | "closed";
    htmlUrl: string;
  };
  citedPullRequest: {
    number: number;
    state: "open" | "closed";
    merged: boolean;
    htmlUrl: string;
  } | null;
  patternCheck: PatternCheck | null;
  verdict: Verdict;
  reason: string;
}

export interface GitHubClient {
  getIssue(ref: IssueRef): Promise<GitHubIssue>;
  getIssueComments(ref: IssueRef): Promise<GitHubComment[]>;
  getPullRequest(owner: string, repo: string, number: number): Promise<GitHubPullRequest>;
  getFileContent(owner: string, repo: string, path: string, ref?: string): Promise<string | null>;
}

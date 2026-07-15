import type { GitHubClient, GitHubComment, GitHubIssue, GitHubPullRequest, IssueRef } from "../src/types.js";

export interface MockFixture {
  issues: Record<number, GitHubIssue>;
  comments: Record<number, GitHubComment[]>;
  pulls: Record<number, GitHubPullRequest>;
  files: Record<string, string>;
}

export class MockGitHubClient implements GitHubClient {
  constructor(private readonly fixture: MockFixture) {}

  async getIssue(ref: IssueRef): Promise<GitHubIssue> {
    const issue = this.fixture.issues[ref.number];
    if (!issue) throw new Error(`fixture missing issue #${ref.number}`);
    return issue;
  }

  async getIssueComments(ref: IssueRef): Promise<GitHubComment[]> {
    return this.fixture.comments[ref.number] ?? [];
  }

  async getPullRequest(_owner: string, _repo: string, number: number): Promise<GitHubPullRequest> {
    const pr = this.fixture.pulls[number];
    if (!pr) throw new Error(`fixture missing PR #${number}`);
    return pr;
  }

  async getFileContent(_owner: string, _repo: string, path: string): Promise<string | null> {
    return this.fixture.files[path] ?? null;
  }
}

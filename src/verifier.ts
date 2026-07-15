import type { GitHubClient, IssueRef, VerificationResult } from "./types.js";
import type { PatternMatcher } from "./pattern-matcher.js";

const FIX_REFERENCE_PATTERN = /\b(?:fixed|resolved|closed|addressed)\s+(?:in|by|via)?\s*(?:pr\s*)?#(\d+)/i;

/**
 * Extracts the PR number a piece of text claims fixed an issue, e.g.
 * "Fixed in PR #52", "fixed by #52", "resolved in #52". Returns the last
 * match found (closing comments are usually the most authoritative and
 * tend to come after earlier discussion in the same body/thread).
 */
export function extractFixReference(text: string): number | null {
  const matches = [...text.matchAll(new RegExp(FIX_REFERENCE_PATTERN, "gi"))];
  if (matches.length === 0) return null;
  const last = matches[matches.length - 1];
  const raw = last?.[1];
  if (!raw) return null;
  const num = Number.parseInt(raw, 10);
  return Number.isFinite(num) ? num : null;
}

export interface PatternSpec {
  path: string;
  pattern: string;
}

/**
 * Verifies whether issues closed as "fixed" actually have a merged fix.
 * The core, unambiguous check: tracker state (closed, cites a fix PR) vs.
 * actual PR merge state. An optional PatternMatcher adds a secondary,
 * best-effort check for whether the cited vulnerable code pattern is
 * still present at HEAD.
 */
export class TrackerVerifier {
  constructor(
    private readonly client: GitHubClient,
    private readonly patternMatcher?: PatternMatcher,
  ) {}

  async verify(ref: IssueRef, patternSpec?: PatternSpec): Promise<VerificationResult> {
    const issue = await this.client.getIssue(ref);
    const issueUrl = `https://github.com/${ref.owner}/${ref.repo}/issues/${ref.number}`;

    if (issue.state === "open") {
      return {
        issue: { number: issue.number, title: issue.title, state: issue.state, htmlUrl: issueUrl },
        citedPullRequest: null,
        patternCheck: null,
        verdict: "UNVERIFIED",
        reason: "Issue is still open; no fix has been claimed.",
      };
    }

    const comments = await this.client.getIssueComments(ref);
    const searchText = [issue.body ?? "", ...comments.map((c) => c.body)].join("\n");
    const prNumber = extractFixReference(searchText);

    if (prNumber === null) {
      return {
        issue: { number: issue.number, title: issue.title, state: issue.state, htmlUrl: issueUrl },
        citedPullRequest: null,
        patternCheck: null,
        verdict: "UNVERIFIED",
        reason: "Issue is closed but no fix PR reference (e.g. \"Fixed in #N\") was found in its body or comments.",
      };
    }

    const pr = await this.client.getPullRequest(ref.owner, ref.repo, prNumber);
    const citedPullRequest = {
      number: pr.number,
      state: pr.state,
      merged: pr.merged,
      htmlUrl: pr.htmlUrl,
    };

    if (!pr.merged) {
      return {
        issue: { number: issue.number, title: issue.title, state: issue.state, htmlUrl: issueUrl },
        citedPullRequest,
        patternCheck: null,
        verdict: "MISMATCH",
        reason: `Issue is closed and cites PR #${prNumber} as the fix, but that PR is ${pr.state} and was never merged.`,
      };
    }

    if (!patternSpec || !this.patternMatcher) {
      return {
        issue: { number: issue.number, title: issue.title, state: issue.state, htmlUrl: issueUrl },
        citedPullRequest,
        patternCheck: null,
        verdict: "MATCH",
        reason: `Issue is closed and PR #${prNumber} is merged.`,
      };
    }

    const patternCheck = await this.patternMatcher.check(ref.owner, ref.repo, patternSpec.path, patternSpec.pattern);

    if (patternCheck.found === true) {
      return {
        issue: { number: issue.number, title: issue.title, state: issue.state, htmlUrl: issueUrl },
        citedPullRequest,
        patternCheck,
        verdict: "MISMATCH",
        reason: `PR #${prNumber} is merged, but the cited vulnerable pattern is still present in ${patternSpec.path} at HEAD.`,
      };
    }

    if (patternCheck.found === null) {
      return {
        issue: { number: issue.number, title: issue.title, state: issue.state, htmlUrl: issueUrl },
        citedPullRequest,
        patternCheck,
        verdict: "MATCH",
        reason: `Issue is closed and PR #${prNumber} is merged. Pattern check inconclusive: ${patternCheck.note ?? "unknown"}.`,
      };
    }

    return {
      issue: { number: issue.number, title: issue.title, state: issue.state, htmlUrl: issueUrl },
      citedPullRequest,
      patternCheck,
      verdict: "MATCH",
      reason: `Issue is closed, PR #${prNumber} is merged, and the cited pattern is confirmed absent from ${patternSpec.path} at HEAD.`,
    };
  }
}

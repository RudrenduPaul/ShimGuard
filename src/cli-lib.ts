import { readFileSync } from "node:fs";
import type { PatternSpec } from "./verifier.js";
import type { VerificationResult } from "./types.js";

export interface PatternsFile {
  [issueNumber: string]: PatternSpec;
}

export function parseRepoSlug(slug: string): { owner: string; repo: string } {
  const parts = slug.split("/");
  if (parts.length !== 2 || !parts[0] || !parts[1]) {
    throw new Error(`Invalid repo "${slug}". Expected "<owner>/<repo>".`);
  }
  return { owner: parts[0], repo: parts[1] };
}

export function parseIssueList(raw: string): number[] {
  const nums = raw
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
    .map((s) => Number.parseInt(s, 10));
  if (nums.length === 0 || nums.some((n) => !Number.isFinite(n) || n <= 0)) {
    throw new Error(`Invalid --issues value "${raw}". Expected a comma-separated list of positive integers.`);
  }
  return nums;
}

export function loadPatterns(path: string | undefined): PatternsFile {
  if (!path) return {};
  const raw = readFileSync(path, "utf-8");
  const parsed: unknown = JSON.parse(raw);
  if (typeof parsed !== "object" || parsed === null) {
    throw new Error(`--patterns file "${path}" must contain a JSON object.`);
  }
  return parsed as PatternsFile;
}

export function summarize(results: VerificationResult[]): { mismatch: number; match: number; unverified: number } {
  return {
    mismatch: results.filter((r) => r.verdict === "MISMATCH").length,
    match: results.filter((r) => r.verdict === "MATCH").length,
    unverified: results.filter((r) => r.verdict === "UNVERIFIED").length,
  };
}

export function formatText(results: VerificationResult[], repoSlug: string): string {
  const lines: string[] = [`ShimGuard v0.1 -- Tracker Verification: ${repoSlug}`, ""];
  for (const r of results) {
    const label = r.verdict === "MISMATCH" ? "MISMATCH" : r.verdict === "MATCH" ? "MATCH   " : "UNKNOWN ";
    lines.push(`[${label}] Issue #${r.issue.number} "${r.issue.title}"`);
    lines.push(`  ${r.issue.htmlUrl}`);
    if (r.citedPullRequest) {
      lines.push(
        `  Cited fix: PR #${r.citedPullRequest.number} (${r.citedPullRequest.merged ? "merged" : `${r.citedPullRequest.state}, not merged`})`,
      );
    }
    if (r.patternCheck) {
      const status = r.patternCheck.found === null ? "inconclusive" : r.patternCheck.found ? "still present" : "absent";
      lines.push(`  Pattern check (${r.patternCheck.path}): ${status}`);
    }
    lines.push(`  ${r.reason}`, "");
  }
  const { mismatch, match, unverified } = summarize(results);
  lines.push(`Summary: ${mismatch} MISMATCH, ${match} MATCH, ${unverified} UNVERIFIED (${results.length} checked)`);
  return lines.join("\n");
}

export function formatJson(results: VerificationResult[], repoSlug: string): string {
  const { mismatch, match, unverified } = summarize(results);
  return JSON.stringify(
    {
      repo: repoSlug,
      checked: results.length,
      summary: { mismatch, match, unverified },
      results,
    },
    null,
    2,
  );
}

import { describe, expect, it } from "vitest";
import { writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { parseRepoSlug, parseIssueList, loadPatterns, formatText, formatJson, summarize } from "../src/cli-lib.js";
import type { VerificationResult } from "../src/types.js";

describe("parseRepoSlug", () => {
  it("parses a valid owner/repo slug", () => {
    expect(parseRepoSlug("sybil-solutions/codex-shim")).toEqual({ owner: "sybil-solutions", repo: "codex-shim" });
  });

  it("throws on a slug with no slash", () => {
    expect(() => parseRepoSlug("not-a-slug")).toThrow(/Invalid repo/);
  });

  it("throws on a slug with too many slashes", () => {
    expect(() => parseRepoSlug("a/b/c")).toThrow(/Invalid repo/);
  });

  it("throws on an empty owner or repo segment", () => {
    expect(() => parseRepoSlug("/repo")).toThrow(/Invalid repo/);
    expect(() => parseRepoSlug("owner/")).toThrow(/Invalid repo/);
  });
});

describe("parseIssueList", () => {
  it("parses a comma-separated list", () => {
    expect(parseIssueList("38,41,42")).toEqual([38, 41, 42]);
  });

  it("trims whitespace around numbers", () => {
    expect(parseIssueList(" 38 , 41 ")).toEqual([38, 41]);
  });

  it("throws on an empty string", () => {
    expect(() => parseIssueList("")).toThrow(/Invalid --issues/);
  });

  it("throws on a non-numeric entry", () => {
    expect(() => parseIssueList("38,abc")).toThrow(/Invalid --issues/);
  });

  it("throws on a zero or negative entry", () => {
    expect(() => parseIssueList("0")).toThrow(/Invalid --issues/);
    expect(() => parseIssueList("-1")).toThrow(/Invalid --issues/);
  });
});

describe("loadPatterns", () => {
  it("returns an empty object when no path is given", () => {
    expect(loadPatterns(undefined)).toEqual({});
  });

  it("loads and parses a valid patterns JSON file", () => {
    const dir = mkdtempSync(join(tmpdir(), "shimguard-test-"));
    const file = join(dir, "patterns.json");
    writeFileSync(file, JSON.stringify({ "45": { path: "settings.py", pattern: "cursor_key_fallback" } }));
    expect(loadPatterns(file)).toEqual({ "45": { path: "settings.py", pattern: "cursor_key_fallback" } });
  });

  it("throws when the file does not contain a JSON object", () => {
    const dir = mkdtempSync(join(tmpdir(), "shimguard-test-"));
    const file = join(dir, "patterns.json");
    writeFileSync(file, JSON.stringify("not-an-object"));
    expect(() => loadPatterns(file)).toThrow(/must contain a JSON object/);
  });
});

const sampleResults: VerificationResult[] = [
  {
    issue: { number: 45, title: "Key leak", state: "closed", htmlUrl: "https://example.com/issues/45" },
    citedPullRequest: { number: 52, state: "open", merged: false, htmlUrl: "https://example.com/pull/52" },
    patternCheck: null,
    verdict: "MISMATCH",
    reason: "Issue is closed and cites PR #52 as the fix, but that PR is open and was never merged.",
  },
  {
    issue: { number: 100, title: "Fixed thing", state: "closed", htmlUrl: "https://example.com/issues/100" },
    citedPullRequest: { number: 101, state: "closed", merged: true, htmlUrl: "https://example.com/pull/101" },
    patternCheck: null,
    verdict: "MATCH",
    reason: "Issue is closed and PR #101 is merged.",
  },
];

describe("summarize", () => {
  it("counts verdicts correctly", () => {
    expect(summarize(sampleResults)).toEqual({ mismatch: 1, match: 1, unverified: 0 });
  });
});

describe("formatText", () => {
  it("includes each issue, its verdict, and a summary line", () => {
    const out = formatText(sampleResults, "sybil-solutions/codex-shim");
    expect(out).toMatch(/MISMATCH.*Issue #45/);
    expect(out).toMatch(/MATCH.*Issue #100/);
    expect(out).toMatch(/Summary: 1 MISMATCH, 1 MATCH, 0 UNVERIFIED \(2 checked\)/);
  });
});

describe("formatJson", () => {
  it("produces valid, parseable JSON with the expected shape", () => {
    const out = formatJson(sampleResults, "sybil-solutions/codex-shim");
    const parsed = JSON.parse(out);
    expect(parsed.repo).toBe("sybil-solutions/codex-shim");
    expect(parsed.checked).toBe(2);
    expect(parsed.summary).toEqual({ mismatch: 1, match: 1, unverified: 0 });
    expect(parsed.results).toHaveLength(2);
  });
});

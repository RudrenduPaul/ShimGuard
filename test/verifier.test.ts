import { describe, expect, it } from "vitest";
import { TrackerVerifier, extractFixReference } from "../src/verifier.js";
import { RegexPatternMatcher } from "../src/pattern-matcher.js";
import { MockGitHubClient, type MockFixture } from "./mock-client.js";

// Fixture modeled on the real, independently-verified sybil-solutions/codex-shim
// case: issues #45/#46 were closed citing "Fixed in PR #52", but PR #52 was
// never merged. Numbers/text are illustrative snapshots of that verified case,
// not a live network fetch.
const codexShimFixture: MockFixture = {
  issues: {
    45: {
      number: 45,
      title: "Cross-provider API key fallback leaks credentials to unintended host",
      state: "closed",
      body: "_resolve_api_key falls back to the Cursor API key for any model entry with an unresolved key, regardless of provider or base_url.",
      closedAt: "2026-06-22T00:00:00Z",
    },
    46: {
      number: 46,
      title: "Debug request dump writes full conversation bodies to disk",
      state: "closed",
      body: "_dump_debug_request writes full conversation bodies to .codex-shim/last_request.json with default file permissions.",
      closedAt: "2026-06-22T00:00:00Z",
    },
    100: {
      number: 100,
      title: "Genuinely fixed issue",
      state: "closed",
      body: "Some bug.",
      closedAt: "2026-06-01T00:00:00Z",
    },
    200: {
      number: 200,
      title: "Closed with no fix reference",
      state: "closed",
      body: "Closing as stale, no fix applied.",
      closedAt: "2026-06-01T00:00:00Z",
    },
    300: {
      number: 300,
      title: "Still-open issue",
      state: "open",
      body: "Investigating.",
      closedAt: null,
    },
  },
  comments: {
    45: [{ body: "Fixed in PR #52", createdAt: "2026-06-22T00:00:00Z" }],
    46: [{ body: "Fixed in PR #52", createdAt: "2026-06-22T00:00:00Z" }],
    100: [{ body: "Fixed in #101", createdAt: "2026-06-01T00:00:00Z" }],
    200: [],
    300: [],
  },
  pulls: {
    52: {
      number: 52,
      state: "open",
      merged: false,
      mergedAt: null,
      htmlUrl: "https://github.com/sybil-solutions/codex-shim/pull/52",
    },
    101: {
      number: 101,
      state: "closed",
      merged: true,
      mergedAt: "2026-06-01T12:00:00Z",
      htmlUrl: "https://example.com/pull/101",
    },
  },
  files: {
    "codex_shim/settings.py": "def _resolve_api_key():\n    return cursor_key_fallback()\n",
    "src/fixed_file.py": "def clean():\n    pass\n",
  },
};

function buildVerifier(fixture: MockFixture) {
  const client = new MockGitHubClient(fixture);
  const matcher = new RegexPatternMatcher(client);
  return new TrackerVerifier(client, matcher);
}

describe("extractFixReference", () => {
  it("extracts a PR number from 'Fixed in PR #52'", () => {
    expect(extractFixReference("Fixed in PR #52")).toBe(52);
  });

  it("extracts a PR number from 'fixed by #101'", () => {
    expect(extractFixReference("This was fixed by #101 last week.")).toBe(101);
  });

  it("returns the last reference when multiple appear", () => {
    expect(extractFixReference("Related to #10. Fixed in #20.")).toBe(20);
  });

  it("returns null when no fix reference is present", () => {
    expect(extractFixReference("Closing as stale.")).toBeNull();
  });
});

describe("TrackerVerifier", () => {
  it("returns MISMATCH when the cited PR is closed but not merged (real codex-shim case, issue #45)", async () => {
    const verifier = buildVerifier(codexShimFixture);
    const result = await verifier.verify({ owner: "sybil-solutions", repo: "codex-shim", number: 45 });
    expect(result.verdict).toBe("MISMATCH");
    expect(result.citedPullRequest?.number).toBe(52);
    expect(result.citedPullRequest?.merged).toBe(false);
    expect(result.reason).toMatch(/never merged/);
  });

  it("returns MISMATCH for issue #46 sharing the same unmerged PR #52", async () => {
    const verifier = buildVerifier(codexShimFixture);
    const result = await verifier.verify({ owner: "sybil-solutions", repo: "codex-shim", number: 46 });
    expect(result.verdict).toBe("MISMATCH");
    expect(result.citedPullRequest?.number).toBe(52);
  });

  it("returns MATCH when the cited PR is actually merged", async () => {
    const verifier = buildVerifier(codexShimFixture);
    const result = await verifier.verify({ owner: "test", repo: "repo", number: 100 });
    expect(result.verdict).toBe("MATCH");
    expect(result.citedPullRequest?.merged).toBe(true);
  });

  it("returns UNVERIFIED when a closed issue cites no fix PR", async () => {
    const verifier = buildVerifier(codexShimFixture);
    const result = await verifier.verify({ owner: "test", repo: "repo", number: 200 });
    expect(result.verdict).toBe("UNVERIFIED");
    expect(result.citedPullRequest).toBeNull();
  });

  it("returns UNVERIFIED for a still-open issue", async () => {
    const verifier = buildVerifier(codexShimFixture);
    const result = await verifier.verify({ owner: "test", repo: "repo", number: 300 });
    expect(result.verdict).toBe("UNVERIFIED");
    expect(result.reason).toMatch(/still open/);
  });

  it("downgrades a merged-PR MATCH to MISMATCH when the vulnerable pattern is still present", async () => {
    const verifier = buildVerifier(codexShimFixture);
    const result = await verifier.verify(
      { owner: "test", repo: "repo", number: 100 },
      { path: "codex_shim/settings.py", pattern: "cursor_key_fallback" },
    );
    expect(result.verdict).toBe("MISMATCH");
    expect(result.patternCheck?.found).toBe(true);
  });

  it("keeps MATCH when the pattern check confirms the vulnerable code is gone", async () => {
    const verifier = buildVerifier(codexShimFixture);
    const result = await verifier.verify(
      { owner: "test", repo: "repo", number: 100 },
      { path: "src/fixed_file.py", pattern: "cursor_key_fallback" },
    );
    expect(result.verdict).toBe("MATCH");
    expect(result.patternCheck?.found).toBe(false);
  });

  it("keeps MATCH with a caveat when the pattern check is inconclusive (file not found)", async () => {
    const verifier = buildVerifier(codexShimFixture);
    const result = await verifier.verify(
      { owner: "test", repo: "repo", number: 100 },
      { path: "does/not/exist.py", pattern: "anything" },
    );
    expect(result.verdict).toBe("MATCH");
    expect(result.patternCheck?.found).toBeNull();
    expect(result.reason).toMatch(/inconclusive/);
  });
});

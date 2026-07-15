import { describe, expect, it } from "vitest";
import { RegexPatternMatcher } from "../src/pattern-matcher.js";
import { MockGitHubClient, type MockFixture } from "./mock-client.js";

function buildMatcher(fixture: MockFixture) {
  return new RegexPatternMatcher(new MockGitHubClient(fixture));
}

const baseFixture: MockFixture = {
  issues: {},
  comments: {},
  pulls: {},
  files: {
    "clean.py": "def clean():\n    pass\n",
    "vulnerable.py": "def leak():\n    return cursor_key_fallback()\n",
    // 35 'a' characters is enough to trigger catastrophic backtracking
    // against (\w+\s*)+$, confirmed with a standalone reproduction.
    "redos-bait.py": "a".repeat(35) + "!",
    "huge.py": "x".repeat(1_100_000),
  },
};

describe("RegexPatternMatcher.check", () => {
  it("returns found=true when the pattern matches", async () => {
    const matcher = buildMatcher(baseFixture);
    const result = await matcher.check("o", "r", "vulnerable.py", "cursor_key_fallback");
    expect(result.found).toBe(true);
  });

  it("returns found=false when the pattern does not match", async () => {
    const matcher = buildMatcher(baseFixture);
    const result = await matcher.check("o", "r", "clean.py", "cursor_key_fallback");
    expect(result.found).toBe(false);
  });

  it("returns found=null with a note when the file does not exist", async () => {
    const matcher = buildMatcher(baseFixture);
    const result = await matcher.check("o", "r", "missing.py", "anything");
    expect(result.found).toBeNull();
    expect(result.note).toMatch(/not found/);
  });

  it("returns found=null with a note for an invalid regex", async () => {
    const matcher = buildMatcher(baseFixture);
    const result = await matcher.check("o", "r", "clean.py", "(unclosed");
    expect(result.found).toBeNull();
    expect(result.note).toMatch(/Invalid pattern regex/);
  });

  it("skips matching and returns found=null when content exceeds the size cap", async () => {
    const matcher = buildMatcher(baseFixture);
    const result = await matcher.check("o", "r", "huge.py", "x+");
    expect(result.found).toBeNull();
    expect(result.note).toMatch(/larger than/);
  });

  it("aborts and returns found=null when the regex catastrophically backtracks (ReDoS guard)", async () => {
    const matcher = buildMatcher(baseFixture);
    const start = Date.now();
    const result = await matcher.check("o", "r", "redos-bait.py", "(\\w+\\s*)+$");
    const elapsed = Date.now() - start;
    expect(result.found).toBeNull();
    expect(result.note).toMatch(/exceeded.*aborted/);
    // The worker has a 2s deadline; the whole check must return well under
    // the time an unguarded catastrophic backtrack would actually take.
    expect(elapsed).toBeLessThan(4_000);
  }, 6_000);
});

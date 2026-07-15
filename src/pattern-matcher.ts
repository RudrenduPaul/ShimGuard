import type { GitHubClient, PatternCheck } from "./types.js";

/**
 * A PatternMatcher checks whether a specific vulnerable pattern is still
 * present in a repo at a given ref. Pluggable so v0.2+ verifiers (e.g. a
 * local shim-config scanner) can supply a different matching strategy
 * without changing TrackerVerifier itself.
 */
export interface PatternMatcher {
  check(owner: string, repo: string, path: string, pattern: string, ref?: string): Promise<PatternCheck>;
}

export class RegexPatternMatcher implements PatternMatcher {
  constructor(private readonly client: GitHubClient) {}

  async check(owner: string, repo: string, path: string, pattern: string, ref = "HEAD"): Promise<PatternCheck> {
    let content: string | null;
    try {
      content = await this.client.getFileContent(owner, repo, path, ref);
    } catch (err) {
      return {
        path,
        pattern,
        found: null,
        note: `Could not fetch ${path}: ${err instanceof Error ? err.message : String(err)}`,
      };
    }

    if (content === null) {
      return { path, pattern, found: null, note: `${path} not found at ${ref}` };
    }

    let regex: RegExp;
    try {
      regex = new RegExp(pattern);
    } catch {
      return { path, pattern, found: null, note: `Invalid pattern regex: ${pattern}` };
    }

    return { path, pattern, found: regex.test(content) };
  }
}

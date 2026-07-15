import { Worker } from "node:worker_threads";
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

// The operator's --patterns regex is tested against content fetched live
// from the target repo, which by this tool's own purpose may be untrusted.
// A common, non-malicious regex shape (e.g. "(\w+\s*)+$") can still hang
// indefinitely (catastrophic backtracking) against adversarial content --
// confirmed with a local reproduction. Node has no native regex timeout, so
// the match runs in a throwaway worker thread that gets terminated on a
// hard deadline instead of running inline on the main thread.
const MAX_CONTENT_BYTES = 1_000_000;
const REGEX_TIMEOUT_MS = 2_000;

const WORKER_SOURCE = `
import { parentPort, workerData } from "node:worker_threads";
const { pattern, content } = workerData;
try {
  const found = new RegExp(pattern).test(content);
  parentPort.postMessage({ found });
} catch {
  parentPort.postMessage({ error: "invalid-regex" });
}
`;

interface WorkerFound {
  found: boolean;
}
interface WorkerInvalid {
  error: "invalid-regex";
}
type WorkerResult = WorkerFound | WorkerInvalid | { timedOut: true } | { error: "worker-error" };

function runRegexWithTimeout(pattern: string, content: string, timeoutMs: number): Promise<WorkerResult> {
  return new Promise((resolve) => {
    const url = new URL(`data:text/javascript,${encodeURIComponent(WORKER_SOURCE)}`);
    const worker = new Worker(url, { workerData: { pattern, content } });
    let settled = false;

    const finish = (result: WorkerResult) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      void worker.terminate();
      resolve(result);
    };

    const timer = setTimeout(() => finish({ timedOut: true }), timeoutMs);

    worker.once("message", (msg: WorkerResult) => finish(msg));
    worker.once("error", () => finish({ error: "worker-error" }));
  });
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

    if (content.length > MAX_CONTENT_BYTES) {
      return {
        path,
        pattern,
        found: null,
        note: `${path} is larger than ${MAX_CONTENT_BYTES} bytes at ${ref}; skipped to bound matching cost`,
      };
    }

    const result = await runRegexWithTimeout(pattern, content, REGEX_TIMEOUT_MS);

    if ("timedOut" in result) {
      return {
        path,
        pattern,
        found: null,
        note: `Pattern match against ${path} exceeded ${REGEX_TIMEOUT_MS}ms and was aborted (likely catastrophic regex backtracking)`,
      };
    }
    if ("error" in result) {
      return {
        path,
        pattern,
        found: null,
        note: result.error === "invalid-regex" ? `Invalid pattern regex: ${pattern}` : `Pattern match against ${path} failed unexpectedly`,
      };
    }

    return { path, pattern, found: result.found };
  }
}

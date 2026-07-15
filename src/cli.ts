#!/usr/bin/env node
import { Command } from "commander";
import { TrackerVerifier } from "./verifier.js";
import { RegexPatternMatcher } from "./pattern-matcher.js";
import { RestGitHubClient, GitHubApiError } from "./github.js";
import type { VerificationResult } from "./types.js";
import { parseRepoSlug, parseIssueList, loadPatterns, formatText, formatJson } from "./cli-lib.js";

const program = new Command();

program
  .name("shimguard")
  .description(
    "Verify that GitHub issues closed as \"fixed\" actually have a merged fix. Catches security issues marked fixed whose PR was never merged.",
  )
  .version("0.1.0");

program
  .command("verify")
  .description("Check whether closed issues in a repo actually have a merged fix")
  .argument("<repo>", "target repo as <owner>/<repo>, e.g. sybil-solutions/codex-shim")
  .requiredOption("--issues <numbers>", "comma-separated issue numbers to check, e.g. 38,41,42")
  .option("--patterns <file>", "JSON file mapping issue number -> {path, pattern} for an optional code-pattern check")
  .option("--token <token>", "GitHub token for higher API rate limits (defaults to $GITHUB_TOKEN)")
  .option("--format <format>", "output format: text or json", "text")
  .action(async (repoArg: string, opts: { issues: string; patterns?: string; token?: string; format: string }) => {
    try {
      if (opts.format !== "text" && opts.format !== "json") {
        throw new Error(`Invalid --format "${opts.format}". Expected "text" or "json".`);
      }

      const { owner, repo } = parseRepoSlug(repoArg);
      const issueNumbers = parseIssueList(opts.issues);
      const patterns = loadPatterns(opts.patterns);
      const token = opts.token ?? process.env.GITHUB_TOKEN;

      const client = new RestGitHubClient(token);
      const matcher = new RegexPatternMatcher(client);
      const verifier = new TrackerVerifier(client, matcher);

      const results: VerificationResult[] = [];
      for (const number of issueNumbers) {
        const spec = patterns[String(number)];
        results.push(await verifier.verify({ owner, repo, number }, spec));
      }

      console.log(opts.format === "json" ? formatJson(results, repoArg) : formatText(results, repoArg));

      const hasMismatch = results.some((r) => r.verdict === "MISMATCH");
      process.exit(hasMismatch ? 1 : 0);
    } catch (err) {
      if (err instanceof GitHubApiError || err instanceof Error) {
        console.error(`Error: ${err.message}`);
      } else {
        console.error(`Error: ${String(err)}`);
      }
      process.exit(2);
    }
  });

program.parseAsync(process.argv);

# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - Security fix

**Security:** fixed a ReDoS (Regular Expression Denial of Service) vulnerability in
the core `verify` command's fix-reference extraction (`extractFixReference` in
`src/verifier.ts`). The regex used to match connector words (`in`/`by`/`via`/`pr`)
allowed catastrophic backtracking and could hang for many seconds on a crafted
issue body or comment — text that is fetched live from the target repo on every
`shimguard verify` call, with no `--patterns` flag or opt-in required. The
connector matching was rewritten as a single bounded `{0,80}` character class,
making catastrophic backtracking mathematically impossible regardless of input
size, with no behavior change on real input. A regression test now asserts the
extraction completes in under 500ms against a 2,000,000-character adversarial
input.

Commit: `de2ae61`

## [0.1.1] - Security fix

**Security:** two fixes from a security audit pass.

- **High:** `RegexPatternMatcher.check()` compiled the operator-supplied
  `--patterns` regex and ran it unbounded against live content from the
  audited repo, which can hang indefinitely on an adversarial pattern/content
  combination (e.g. `(\w+\s*)+$` against a short adversarial string). Fixed by
  running the match in a worker thread with a 2s hard deadline (terminated on
  timeout, reported as `found: null` with a note) and skipping file content
  over 1MB.
- **Medium:** the CI workflow pinned `actions/checkout` and
  `actions/setup-node` to mutable `@v4` tags instead of commit SHAs, a
  supply-chain exposure if either upstream action were compromised. Pinned
  both to the exact SHAs already in use (no version change).

Also fixed the `bin` path in `package.json` (dropped a leading `./`) to match
what actually shipped in `shimguard-cli@0.1.0`.

Commit: `2b8d525`

## [0.1.0] - Initial release

Initial release of ShimGuard: verifies that a GitHub issue closed as "fixed in
PR #N" actually has that PR merged, and optionally whether the cited
vulnerable code pattern is gone from HEAD. TypeScript CLI and library with a
`TrackerVerifier`/`PatternMatcher` architecture, 94% test coverage.

Commit: `4fd535e`

# Changelog

All notable changes to this project are documented in this file, covering
both distributions -- the npm package (`shimguard-cli`, JS/TS) and the PyPI
package (`shimguard-cli`, Python) -- since they implement the same
verification logic against the same GitHub REST API; entries note which
distribution they apply to.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Python 0.1.0] - 2026-07-16

Initial public release of the Python port, published to PyPI as
`shimguard-cli` (`pip install shimguard-cli`). Complementary to, not a
replacement for, the existing npm package -- both are first-class and
maintained together. See `python/README.md` for Python-specific usage.

### Added

- `shimguard verify <owner>/<repo> --issues <numbers>` CLI (console script
  `shimguard`, package `shimguard`) with the same flags as the npm CLI:
  `--issues`, `--patterns`, `--token`, `--format` (text/json).
- Programmatic library API: `from shimguard import TrackerVerifier,
  RestGitHubClient, RegexPatternMatcher, IssueRef`, returning the same
  structured `VerificationResult` shape (`issue`, `cited_pull_request`,
  `pattern_check`, `verdict`, `reason`).
- `TrackerVerifier` and `extract_fix_reference` reimplemented as genuine
  Python logic against the same ReDoS-safe bounded regex the npm CLI's
  v0.1.2 fix introduced -- ported already fixed, no vulnerable intermediate
  state ever shipped in the Python package.
- `RegexPatternMatcher` reimplemented with the same 2-second timeout / 1MB
  content cap as the npm CLI's v0.1.1 fix, using a `multiprocessing.Process`
  in place of a Node worker thread (Python threads cannot be force-killed
  out of a C-level regex loop the way a worker thread can be terminated;
  a subprocess can be sent a real `SIGTERM` instead) -- see
  [SECURITY.md](./SECURITY.md) for the full mechanism comparison.
- Full pytest suite (49 tests) ported from the TypeScript vitest suite:
  fix-reference extraction and its ReDoS regression test, the pattern
  matcher and its ReDoS regression test, tracker-verdict logic across all
  MATCH/MISMATCH/UNVERIFIED paths, CLI argument parsing and output
  formatting, and HTTP-mocked tests for the GitHub REST client, plus one
  live test against the real, currently-open `sybil-solutions/codex-shim#45`
  / PR #52 case.

### Notes

- Verified live against the real, documented `sybil-solutions/codex-shim`
  case: `shimguard verify sybil-solutions/codex-shim --issues 45,46` reports
  2 MISMATCH under the Python CLI, matching the npm CLI's documented output
  for the same repo and issues.

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

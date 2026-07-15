# Security Policy

## Reporting a vulnerability

Open a GitHub issue at https://github.com/RudrenduPaul/ShimGuard/issues, or
for anything sensitive, use GitHub's private vulnerability reporting
(Security tab on the repo).

## Known trust boundaries

ShimGuard's whole purpose is auditing repos you may not fully trust, and
that repo's own content (issue bodies, comments, file contents) flows
directly into two places that used to run unbounded regex matching against
it. Both are fixed; documented here because the failure mode (ReDoS from
attacker-controlled content matched by an otherwise-ordinary regex) is a
real, recurring category worth naming explicitly rather than treating as
one-off bugs.

**1. The core `verify` command's fix-reference extraction (all versions
before v0.1.2).** Every `shimguard verify` call scans each issue's body and
comments for a phrase like "Fixed in PR #52" using a regex. The original
pattern's connector-word matching (`\s+(?:in|by|via)?\s*(?:pr\s*)?`) allowed
catastrophic backtracking against a long, keyword-free block of text ending
without a `#N` reference. Confirmed with a working reproduction: a
~2,000,000-character adversarial issue comment hung the match for many
seconds with no cap and no timeout, on the CORE command, with no
`--patterns` flag or any other opt-in required. **Fixed in v0.1.2**: the
connector-matching is now a single bounded `{0,80}` character class instead
of chained optional/greedy groups, which makes backtracking mathematically
impossible regardless of input size (verified at 0ms against a
2,000,000-character adversarial input).

**2. The optional `--patterns` code check (all versions before v0.1.1).**
The `--patterns` flag accepts a JSON file mapping issue numbers to a
`{path, pattern}` pair, where `pattern` is compiled as a JavaScript `RegExp`
and tested against file content fetched live from the target repo. The
realistic risk is not a malicious `--patterns` file someone hands you
(though that's also worth reviewing before use): it's that a completely
ordinary regex you write yourself, tested against adversarial content served
by an untrusted target repo, can trigger catastrophic backtracking.
Confirmed with a working reproduction: an everyday pattern like
`(\w+\s*)+$` hung against a 36-byte adversarial string. **Fixed in v0.1.1**:
the regex match now runs in a worker thread with a 2-second hard deadline
(the worker is terminated if it doesn't finish in time, and the check
reports `found: null` with a note instead of hanging), and file content
over 1MB is skipped rather than matched.

**If you're running a version before v0.1.2, upgrade.** Neither fix changes
any command's public behavior for legitimate input; both only bound
worst-case time against adversarial input.

**GitHub tokens are never logged or included in error output.** `--token`
(or `$GITHUB_TOKEN`) is sent only as an `Authorization` header to
`api.github.com`. Error messages include the request URL and HTTP status,
never the token value.

**Network requests are scoped to `api.github.com` only.** The `owner`/`repo`
arguments become URL path segments, not host segments, so there is no
SSRF surface from user-supplied repo slugs. All requests use a 15-second
timeout to avoid hanging indefinitely.

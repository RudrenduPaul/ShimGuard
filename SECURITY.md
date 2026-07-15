# Security Policy

## Reporting a vulnerability

Open a GitHub issue at https://github.com/RudrenduPaul/ShimGuard/issues, or
for anything sensitive, use GitHub's private vulnerability reporting
(Security tab on the repo).

## Known trust boundaries

**The `--patterns` code check matches against content from the repo you're
auditing, which may not be trustworthy.** The `--patterns` flag accepts a
JSON file mapping issue numbers to a `{path, pattern}` pair, where `pattern`
is compiled as a JavaScript `RegExp` and tested against file content fetched
live from the `<owner>/<repo>` you point ShimGuard at. The realistic risk
here is not a malicious `--patterns` file someone hands you (though that's
also worth reviewing before use): it's that a completely ordinary regex you
write yourself, tested against adversarial content served by an untrusted
target repo, can trigger catastrophic backtracking (ReDoS). A security audit
covering ShimGuard's own codebase confirmed this with a working local
reproduction: an everyday pattern like `(\w+\s*)+$` hung against a 36-byte
adversarial string.

**Mitigated as of v0.1.1:** the regex match now runs in a worker thread with
a 2-second hard deadline (the worker is terminated if it doesn't finish in
time, and the check reports `found: null` with a note instead of hanging),
and file content over 1MB is skipped rather than matched. This does not
affect the core `verify` check (tracker-vs-merge-status), which requires no
`--patterns` file and no regex matching at all.

**GitHub tokens are never logged or included in error output.** `--token`
(or `$GITHUB_TOKEN`) is sent only as an `Authorization` header to
`api.github.com`. Error messages include the request URL and HTTP status,
never the token value.

**Network requests are scoped to `api.github.com` only.** The `owner`/`repo`
arguments become URL path segments, not host segments, so there is no
SSRF surface from user-supplied repo slugs. All requests use a 15-second
timeout to avoid hanging indefinitely.

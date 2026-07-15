# Security Policy

## Reporting a vulnerability

Open a GitHub issue at https://github.com/RudrenduPaul/ShimGuard/issues, or
for anything sensitive, use GitHub's private vulnerability reporting
(Security tab on the repo).

## Known trust boundaries

**`--patterns` files are trusted input, not sandboxed.** The `--patterns`
flag accepts a JSON file mapping issue numbers to a `{path, pattern}` pair,
where `pattern` is compiled directly as a JavaScript `RegExp` and tested
against file content fetched from GitHub. ShimGuard does not sandbox or
time-box this regex evaluation. If you run ShimGuard with a `--patterns`
file you did not author yourself (e.g. one someone else shared with you),
review the `pattern` values first: a maliciously crafted regex with
catastrophic backtracking could hang the process. This does not affect the
core `verify` check (tracker-vs-merge-status), which requires no
`--patterns` file at all.

**GitHub tokens are never logged or included in error output.** `--token`
(or `$GITHUB_TOKEN`) is sent only as an `Authorization` header to
`api.github.com`. Error messages include the request URL and HTTP status,
never the token value.

**Network requests are scoped to `api.github.com` only.** The `owner`/`repo`
arguments become URL path segments, not host segments, so there is no
SSRF surface from user-supplied repo slugs. All requests use a 15-second
timeout to avoid hanging indefinitely.

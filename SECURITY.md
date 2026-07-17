# Security Policy

ShimGuard ships two distributions: the npm package (`shimguard-cli`,
TypeScript, repo root) and the PyPI package (`shimguard-cli`, Python,
`python/`). Both implement the same checks against the same GitHub REST
API and share the same trust-boundary analysis below.

## Supported versions

| Package | Version | Supported |
| --- | --- | --- |
| `shimguard-cli` (npm) | 0.1.x | Yes |
| `shimguard-cli` (PyPI) | 0.1.x | Yes |

Both distributions are pre-1.0 and under active development. Security fixes
land on the latest `0.1.x` release of each; there is no older supported line
to backport to yet.

## Reporting a vulnerability

Open a GitHub issue at https://github.com/RudrenduPaul/ShimGuard/issues, or
for anything sensitive, use GitHub's private vulnerability reporting
(Security tab on the repo, or
[Security Advisories](https://github.com/RudrenduPaul/ShimGuard/security/advisories/new)
directly). State which distribution is affected (npm, PyPI, or both).

## Known trust boundaries

ShimGuard's whole purpose is auditing repos you may not fully trust, and
that repo's own content (issue bodies, comments, file contents) flows
directly into two places that used to run unbounded regex matching against
it in the npm package. Both are fixed there and were ported already-fixed
into the Python package; documented here because the failure mode (ReDoS
from attacker-controlled content matched by an otherwise-ordinary regex) is
a real, recurring category worth naming explicitly rather than treating as
one-off bugs.

**1. The core `verify` command's fix-reference extraction (npm: fixed in
v0.1.2; Python: fixed from its first release).** Every `verify` call scans
each issue's body and comments for a phrase like "Fixed in PR #52" using a
regex. An earlier npm version's connector-word matching
(`\s+(?:in|by|via)?\s*(?:pr\s*)?`) allowed catastrophic backtracking against
a long, keyword-free block of text ending without a `#N` reference.
Confirmed with a working reproduction: a ~2,000,000-character adversarial
issue comment hung the match for many seconds with no cap and no timeout,
on the CORE command, with no `--patterns` flag or any other opt-in
required. Both CLIs now use a single bounded `{0,80}` character class
instead of chained optional/greedy groups, which makes backtracking
mathematically impossible regardless of input size (confirmed in both
languages: 0ms against a 2,000,000-character adversarial input in the npm
CLI; under 500ms including Python's own overhead in the Python CLI's own
regression test).

**2. The optional `--patterns` code check (npm: fixed in v0.1.1; Python:
fixed from its first release).** The `--patterns` flag accepts a JSON file
mapping issue numbers to a `{path, pattern}` pair, where `pattern` is
compiled as a regular expression (`RegExp` in the npm CLI, `re` in the
Python CLI) and tested against file content fetched live from the target
repo. The realistic risk is not a malicious `--patterns` file someone hands
you (though that's also worth reviewing before use): it's that a completely
ordinary regex you write yourself, tested against adversarial content
served by an untrusted target repo, can trigger catastrophic backtracking.
Confirmed with a working reproduction in **both** languages: an everyday
pattern like `(\w+\s*)+$` hangs against a 36-byte adversarial string under
both Node's and Python's regex engines.

- **npm CLI**: the regex match runs in a Node worker thread with a
  2-second hard deadline; the worker is terminated if it doesn't finish in
  time, and the check reports `found: null` with a note instead of hanging.
- **Python CLI**: Python's `re` module has no native match timeout, and
  unlike a Node worker thread, a Python *thread* cannot be force-killed out
  of a C-level regex loop. The Python port instead runs the match in a
  `multiprocessing.Process` with the same 2-second deadline, and calls
  `Process.terminate()` (a real `SIGTERM` the OS enforces) if it doesn't
  finish in time -- same guarantee as the npm CLI's worker-thread
  termination, different mechanism, verified with the equivalent
  reproduction ported to the Python test suite.

Both CLIs also skip file content over 1MB rather than matching it.

**If you're running an npm version before v0.1.2, upgrade.** Neither fix
changes any command's public behavior for legitimate input; both only
bound worst-case time against adversarial input. The Python package has
never shipped a version without these guards.

**GitHub tokens are never logged or included in error output.** `--token`
(or `$GITHUB_TOKEN`) is sent only as an `Authorization` header to
`api.github.com`. Error messages include the request URL and HTTP status,
never the token value. This holds in both CLIs.

**Network requests are scoped to `api.github.com` only.** The `owner`/`repo`
arguments become URL path segments, not host segments, so there is no
SSRF surface from user-supplied repo slugs. All requests use a 15-second
timeout to avoid hanging indefinitely, in both CLIs.

## What is out of scope

- Vulnerabilities in a target repo being audited (i.e. the thing ShimGuard
  is checking) -- report those to the target repo's own maintainers.
- The accuracy of the fix-reference regex against closing-comment phrasings
  it doesn't recognize -- that's a detection-coverage gap, open a normal
  issue or PR for it (see [CONTRIBUTING.md](./CONTRIBUTING.md)).

## Response

We aim to acknowledge a report within 5 business days and to have a fix or
a mitigation plan within 30 days for a confirmed, in-scope vulnerability.
Credit is given in the release notes unless you ask to remain anonymous.

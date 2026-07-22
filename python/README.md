# shimguard-cli (Python)

Verify that a GitHub issue closed as "fixed" actually has a merged fix,
before you trust the tracker.

[![PyPI version](https://img.shields.io/pypi/v/shimguard-cli.svg)](https://pypi.org/project/shimguard-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/RudrenduPaul/ShimGuard/blob/main/LICENSE)
[![Python versions](https://img.shields.io/pypi/pyversions/shimguard-cli.svg)](https://pypi.org/project/shimguard-cli/)
[![CI](https://github.com/RudrenduPaul/ShimGuard/actions/workflows/ci.yml/badge.svg)](https://github.com/RudrenduPaul/ShimGuard/actions/workflows/ci.yml)
[![npm version](https://img.shields.io/npm/v/shimguard-cli.svg)](https://www.npmjs.com/package/shimguard-cli)

## Why this exists

Reading an issue tracker, you trust two signals: the issue's `state` (open
or closed) and the maintainer's closing comment ("fixed in #N"). Neither
signal is verified against reality by GitHub itself. A maintainer can close
an issue citing a PR that never merged, an automated bot can close on a
"fixes #N" keyword in a PR description before that PR lands, or a fix can
get reverted after the issue was already closed. ShimGuard checks the one
thing a human skimming issues does not: does the PR the tracker cites as the
fix actually show `merged: true`? This package is the Python distribution --
a genuine, independent port, not a wrapper around the Node binary.

## Install

```bash
pip install shimguard-cli
```

or with [uv](https://docs.astral.sh/uv/):

```bash
uv add shimguard-cli
```

No external binary to fetch: the verification logic ships inside the wheel
as pure Python plus one dependency (`requests`). The complementary JS/TS
distribution installs the same way on the npm side:
`npm install -g shimguard-cli` (or `npx shimguard-cli verify ...` to run it
once without installing) -- see the
[project README](https://github.com/RudrenduPaul/ShimGuard#readme) for that
package. Both are first-class, maintained together; neither is deprecated in
favor of the other.

## Quickstart

```bash
shimguard verify sybil-solutions/codex-shim --issues 45,46
```

Real output against the real, currently-live `sybil-solutions/codex-shim`
repo (verified directly against the GitHub API while building this port):

```
ShimGuard v0.1 -- Tracker Verification: sybil-solutions/codex-shim

[MISMATCH] Issue #45 "_resolve_api_key silently falls back to Cursor API key for any model with an empty api_key, forwarding it to arbitrary upstream URLs"
  https://github.com/sybil-solutions/codex-shim/issues/45
  Cited fix: PR #52 (open, not merged)
  Issue is closed and cites PR #52 as the fix, but that PR is open and was never merged.

[MISMATCH] Issue #46 "Debug request dump writes full conversation bodies to disk"
  https://github.com/sybil-solutions/codex-shim/issues/46
  Cited fix: PR #52 (open, not merged)
  Issue is closed and cites PR #52 as the fix, but that PR is open and was never merged.

Summary: 2 MISMATCH, 0 MATCH, 0 UNVERIFIED (2 checked)
```

Exit code is `1` when any MISMATCH is found (useful for gating CI), `0` when
every checked issue's claimed fix actually merged, `2` on a usage or network
error.

### Optional: verify the code, not just the merge status

```bash
cat > patterns.json <<'EOF'
{
  "45": { "path": "codex_shim/settings.py", "pattern": "cursor_key_fallback" }
}
EOF

shimguard verify sybil-solutions/codex-shim --issues 45 --patterns patterns.json
```

If the PR is merged but the cited pattern is still present in the file at
`HEAD`, ShimGuard still reports `MISMATCH`. **Trust boundary:** `pattern` is
compiled as a Python regular expression. Only point `--patterns` at files
you wrote or reviewed yourself -- see
[SECURITY.md](https://github.com/RudrenduPaul/ShimGuard/blob/main/SECURITY.md).

Or call the library directly (the agent-native path):

```python
from shimguard import TrackerVerifier, RestGitHubClient, RegexPatternMatcher, IssueRef

client = RestGitHubClient()  # or RestGitHubClient(token=os.environ["GITHUB_TOKEN"])
verifier = TrackerVerifier(client, RegexPatternMatcher(client))

result = verifier.verify(IssueRef(owner="sybil-solutions", repo="codex-shim", number=45))
print(result.verdict)  # "MISMATCH"
```

## How it works

```
<owner>/<repo> + issue numbers
   -> fetch issue (state, body) + comments
   -> extract "Fixed in PR #N" style reference
   -> fetch PR #N, check merged == true
   -> (optional) fetch file at HEAD, check whether --patterns regex still matches
   -> verdict: MATCH / MISMATCH / UNVERIFIED -> exit code
```

`TrackerVerifier` takes any object implementing the `GitHubClient` protocol
and an optional `PatternMatcher`, both are structural (`typing.Protocol`)
interfaces, so a different code host or a different matching strategy can
plug in without changing the verifier itself -- same extension point as the
npm package's `GitHubClient`/`PatternMatcher` TypeScript interfaces.

## CLI reference

```
usage: shimguard [-h] [--version] {verify} ...

Verify that GitHub issues closed as "fixed" actually have a merged fix.
Catches security issues marked fixed whose PR was never merged.
```

```
usage: shimguard verify [-h] --issues ISSUES [--patterns PATTERNS]
                         [--token TOKEN] [--format FORMAT]
                         repo

positional arguments:
  repo                  target repo as <owner>/<repo>, e.g.
                        sybil-solutions/codex-shim

options:
  --issues ISSUES       comma-separated issue numbers to check, e.g.
                        38,41,42
  --patterns PATTERNS   JSON file mapping issue number -> {path, pattern}
                        for an optional code-pattern check
  --token TOKEN         GitHub token for higher API rate limits (defaults
                        to $GITHUB_TOKEN)
  --format FORMAT       output format: "text" or "json" (default: "text")
```

`--format json` output is stable and designed for scripts and AI agents to
parse directly (field names match the npm CLI's JSON output exactly):

```json
{
  "repo": "sybil-solutions/codex-shim",
  "checked": 1,
  "summary": { "mismatch": 1, "match": 0, "unverified": 0 },
  "results": [
    {
      "issue": { "number": 45, "title": "...", "state": "closed", "htmlUrl": "..." },
      "citedPullRequest": { "number": 52, "state": "open", "merged": false, "htmlUrl": "..." },
      "patternCheck": null,
      "verdict": "MISMATCH",
      "reason": "Issue is closed and cites PR #52 as the fix, but that PR is open and was never merged."
    }
  ]
}
```

## Fidelity to the npm package

This is a genuine Python reimplementation of the same detection logic in
`src/verifier.ts` and `src/pattern-matcher.ts`, not a wrapper around the
Node binary. One implementation detail differs by necessity: the TypeScript
`RegexPatternMatcher` runs the `--patterns` regex match in a Node worker
thread with a hard timeout so a catastrophic-backtracking regex can be
force-terminated; Python's `re` module has no equivalent thread-level kill
switch, so this port runs the match in a subprocess
(`multiprocessing.Process`) instead and terminates that process on the same
2-second deadline -- same guarantee (a hung match cannot block the CLI
forever), different mechanism. See
[SECURITY.md](https://github.com/RudrenduPaul/ShimGuard/blob/main/SECURITY.md)
for the full threat model.

## How it compares

No existing open-source tool checks "this issue tracker says
fixed-in-PR-#N, is #N actually merged." The closest adjacent tools solve
different problems -- the full comparison, including why
[wow-actions/auto-close-fixed-issues](https://github.com/wow-actions/auto-close-fixed-issues)
makes this a real, observed failure mode rather than a theoretical one,
lives in the
[project README's "How it compares" section](https://github.com/RudrenduPaul/ShimGuard#how-it-compares).
The short version:

| Tool | What it actually checks | Reads issue tracker / PR merge state? |
|---|---|---|
| **ShimGuard** | Does a GitHub issue's cited "fixed in PR #N" claim match PR #N's real merge state (and, optionally, is the cited code pattern gone from `HEAD`) | Yes, this is the entire check |
| [gitleaks](https://github.com/gitleaks/gitleaks) / [trufflehog](https://github.com/trufflesecurity/trufflehog) | Secrets committed to source (API keys, tokens) | No, scans file content, not tracker state |
| [trivy](https://github.com/aquasecurity/trivy) / [grype](https://github.com/anchore/grype) / [osv-scanner](https://github.com/google/osv-scanner) | Known CVEs in your dependency tree | No, scans a dependency manifest/lockfile, not tracker state |
| [Vanir](https://github.com/google/vanir) (Google) | Whether a known CVE's code signature is still present in a target source tree | No, works from CVE-to-code, doesn't touch a GitHub issue tracker |
| [VFCFinder](https://github.com/s3c2/vfcfinder) (NC State, ASIACCS 2024) | Finds a likely fix commit for an advisory that has *no* linked fix yet | Opposite direction: finds a missing citation, doesn't verify an existing one |

## Testing

```bash
cd python
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

The suite is a full port of the TypeScript vitest suite (fix-reference
extraction, the ReDoS guard, tracker-verdict logic, the pattern matcher, CLI
argument parsing and output formatting), plus HTTP-mocked tests for the
GitHub REST client and one live test against a real, currently-open GitHub
issue/PR pair (`sybil-solutions/codex-shim#45` / PR #52) that skips cleanly
if the network or GitHub's unauthenticated rate limit is unavailable.

## Security

ShimGuard's whole purpose is auditing repos you may not fully trust. It only
makes read-only GitHub API requests -- it never writes, comments, or mutates
anything in the target repo. GitHub tokens are sent only as an
`Authorization` header to `api.github.com` and never logged. See
[SECURITY.md](https://github.com/RudrenduPaul/ShimGuard/blob/main/SECURITY.md)
for the full policy and the ReDoS-mitigation history this port carries
forward from the npm package's v0.1.1/v0.1.2 security fixes.

## FAQ

**Does ShimGuard modify my repo or the target repo?**
No. It only makes read-only GitHub API requests (issues, comments, pull
requests, and optionally file contents). It never writes, comments, or
mutates anything.

**Does it need a GitHub token?**
No for occasional use. Unauthenticated requests work, subject to GitHub's
standard rate limit (60 requests/hour). Set `GITHUB_TOKEN` or pass
`--token` for the higher authenticated limit (5,000 requests/hour),
useful in CI.

**What counts as a "cited fix"?**
ShimGuard looks for phrases like "Fixed in PR #52", "fixed by #101", or
"resolved in #20" in the issue body and its comments, and extracts the
referenced PR number. If no such phrase is found, the result is
`UNVERIFIED`, not `MATCH` or `MISMATCH`: ShimGuard never guesses.

**Can I use this in CI?**
Yes. `shimguard verify` exits `1` when any MISMATCH is found, so a CI
step can gate on it directly. `--format json` gives a stable,
parseable report for a bot or dashboard, with field names matching the
npm CLI's JSON output exactly.

**Is this Python package a wrapper around the npm CLI?**
No. It's a genuine, independent reimplementation of the same detection
logic (`src/verifier.ts`, `src/pattern-matcher.ts`), not a wrapper around
the Node binary. The only place the implementations diverge by necessity
is the `--patterns` regex timeout mechanism -- see "Fidelity to the npm
package" above.

## Contributing

See [CONTRIBUTING.md](https://github.com/RudrenduPaul/ShimGuard/blob/main/CONTRIBUTING.md).

## License

MIT, see [LICENSE](https://github.com/RudrenduPaul/ShimGuard/blob/main/LICENSE).

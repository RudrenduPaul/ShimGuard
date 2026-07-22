# ShimGuard

Verify that a GitHub issue closed as "fixed" actually has a merged fix, before you trust the tracker.

[![CI](https://github.com/RudrenduPaul/ShimGuard/actions/workflows/ci.yml/badge.svg)](https://github.com/RudrenduPaul/ShimGuard/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![npm](https://img.shields.io/npm/v/shimguard-cli)](https://www.npmjs.com/package/shimguard-cli)

```bash
npx shimguard-cli verify sybil-solutions/codex-shim --issues 38,41,42,43,45,46
```

That single command against the real `sybil-solutions/codex-shim` repo (1,000+
stars) turns up 6 MISMATCH results: 6 security issues, each closed with a
"Fixed in PR #52" comment, where PR #52 was never actually merged. The
vulnerable code is still in `main` today. Nobody reading the closed issues
would know.

## Why this exists

Reading an issue tracker, you trust two signals: the issue's `state` (open
or closed) and the maintainer's closing comment ("fixed in #N"). Neither
signal is verified against reality by GitHub itself. A maintainer can close
an issue citing a PR that never merged, an automated bot can close on a
"fixes #N" keyword in a PR description before that PR lands, or a fix can
get reverted after the issue was already closed. Any of these leaves a
tracker saying "fixed" about a bug that is still live.

ShimGuard checks the one thing a human skimming issues does not: does the
PR the tracker cites as the fix actually show `merged: true`? It is a small,
mechanical, unambiguous check, not a heuristic or a guess.

## Install

ShimGuard ships two independent, equally first-class packages -- pick
whichever fits your toolchain, or install both. Neither is deprecated in
favor of the other; both implement the same "closed issue cites Fixed in PR
#N, is #N actually merged" check against the same GitHub REST API.

```bash
# npm -- JavaScript/TypeScript CLI + library
npm install -g shimguard-cli
# or run it once with no install
npx shimguard-cli verify <owner>/<repo> --issues <numbers>

# PyPI -- Python CLI + library (genuine port, not a wrapper around the Node binary)
pip install shimguard-cli
```

The npm CLI requires Node.js 18 or later (uses the built-in `fetch` API).
The Python package's CLI entry point is also `shimguard` (e.g. `shimguard
verify sybil-solutions/codex-shim --issues 45,46`); see
[`python/README.md`](./python/README.md) and
[docs/getting-started.md](./docs/getting-started.md) for the Python-specific
walkthrough, and [CHANGELOG.md](./CHANGELOG.md) for each distribution's
version history.

![Installing shimguard-cli from npm and running its first verify command against the real sybil-solutions/codex-shim repo, reporting 2 MISMATCH results](./docs/demo.gif)

## Quickstart

```bash
shimguard verify sybil-solutions/codex-shim --issues 38,41,42,43,45,46
```

```
ShimGuard v0.1 -- Tracker Verification: sybil-solutions/codex-shim

[MISMATCH] Issue #45 "_resolve_api_key silently falls back to Cursor API key for any model with an empty api_key, forwarding it to arbitrary upstream URLs"
  https://github.com/sybil-solutions/codex-shim/issues/45
  Cited fix: PR #52 (open, not merged)
  Issue is closed and cites PR #52 as the fix, but that PR is open and was never merged.

Summary: 6 MISMATCH, 0 MATCH, 0 UNVERIFIED (6 checked)
```

Exit code is `1` when any MISMATCH is found (useful for gating CI), `0` when
every checked issue's claimed fix actually merged, `2` on a usage or network
error.

### Optional: verify the code, not just the merge status

For an even stronger check, point ShimGuard at the specific file and pattern
an issue named as the vulnerable code:

```bash
cat > patterns.json <<'EOF'
{
  "45": { "path": "codex_shim/settings.py", "pattern": "cursor_key_fallback" }
}
EOF

shimguard verify sybil-solutions/codex-shim --issues 45 --patterns patterns.json
```

If the PR is merged but the cited pattern is still present in the file at
`HEAD`, ShimGuard still reports `MISMATCH`: a merged PR does not guarantee
the specific vulnerable line was actually removed.

**Trust boundary:** `pattern` is compiled as a JavaScript `RegExp`, and
`path` is validated to stay within the target repo (no `..` traversal to a
different repo or API endpoint, as of 0.1.3). Only point `--patterns` at
files you wrote or reviewed yourself. See [SECURITY.md](./SECURITY.md).

## CLI reference

```
Usage: shimguard [options] [command]

Verify that GitHub issues closed as "fixed" actually have a merged fix. Catches
security issues marked fixed whose PR was never merged.

Options:
  -V, --version            output the version number
  -h, --help               display help for command

Commands:
  verify [options] <repo>  Check whether closed issues in a repo actually have
                           a merged fix
  help [command]           display help for command
```

```
Usage: shimguard verify [options] <repo>

Check whether closed issues in a repo actually have a merged fix

Arguments:
  repo                target repo as <owner>/<repo>, e.g.
                      sybil-solutions/codex-shim

Options:
  --issues <numbers>  comma-separated issue numbers to check, e.g. 38,41,42
  --patterns <file>   JSON file mapping issue number -> {path, pattern} for an
                      optional code-pattern check
  --token <token>     GitHub token for higher API rate limits (defaults to
                      $GITHUB_TOKEN)
  --format <format>   output format: text or json (default: "text")
  -h, --help          display help for command
```

`--format json` output is stable and designed for scripts and AI agents to
parse directly:

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

![Running shimguard verify with --format json against the real sybil-solutions/codex-shim repo, printing the structured JSON verdict for issue 45](./docs/usage.gif)

## Library API

ShimGuard's verification logic is also importable directly:

```typescript
import { TrackerVerifier, RestGitHubClient, RegexPatternMatcher } from "shimguard-cli";

const client = new RestGitHubClient(process.env.GITHUB_TOKEN);
const verifier = new TrackerVerifier(client, new RegexPatternMatcher(client));

const result = await verifier.verify({ owner: "sybil-solutions", repo: "codex-shim", number: 45 });
console.log(result.verdict); // "MISMATCH"
```

`TrackerVerifier` takes any `GitHubClient` and an optional `PatternMatcher`
(see `src/types.ts`, `src/pattern-matcher.ts`), both are interfaces, so a
future local-config scanner or a different code host can plug in without
changing the verifier itself.

The Python package exposes the same shape:

```python
from shimguard import TrackerVerifier, RestGitHubClient, RegexPatternMatcher, IssueRef

client = RestGitHubClient()  # or RestGitHubClient(token=os.environ["GITHUB_TOKEN"])
verifier = TrackerVerifier(client, RegexPatternMatcher(client))

result = verifier.verify(IssueRef(owner="sybil-solutions", repo="codex-shim", number=45))
print(result.verdict)  # "MISMATCH"
```

## How it compares

No existing open-source tool checks "this issue tracker says fixed-in-PR-#N,
is #N actually merged." That claim is verified by searching for
issue-fix-verification tools, patch-verification tools, and
security-advisory-fix tools before writing this. The closest adjacent tools
solve different problems:

| Tool | What it actually checks | Reads issue tracker / PR merge state? |
|---|---|---|
| **ShimGuard** | Does a GitHub issue's cited "fixed in PR #N" claim match PR #N's real merge state (and, optionally, is the cited code pattern gone from `HEAD`) | Yes, this is the entire check |
| [gitleaks](https://github.com/gitleaks/gitleaks) / [trufflehog](https://github.com/trufflesecurity/trufflehog) | Secrets committed to source (API keys, tokens) | No, scans file content, not tracker state |
| [trivy](https://github.com/aquasecurity/trivy) / [grype](https://github.com/anchore/grype) / [osv-scanner](https://github.com/google/osv-scanner) | Known CVEs in your dependency tree | No, scans a dependency manifest/lockfile, not tracker state |
| [Vanir](https://github.com/google/vanir) (Google) | Whether a known CVE's code signature is still present in a target source tree | No, works from CVE-to-code, doesn't touch a GitHub issue tracker |
| [VFCFinder](https://github.com/s3c2/vfcfinder) (NC State, ASIACCS 2024) | Finds a likely fix commit for an advisory that has *no* linked fix yet | Opposite direction: finds a missing citation, doesn't verify an existing one |

The gap ShimGuard fills is real, not theoretical. [wow-actions/auto-close-fixed-issues](https://github.com/wow-actions/auto-close-fixed-issues),
a GitHub Action used by other repos, closes an issue on a PR's `closed`
event, not its `merged` event: a bot can mark an issue "fixed" the moment
a PR is closed, whether or not it actually merged. GitHub's own native
`Closes #N` keyword linking only auto-closes on a real merge to the default
branch, so this specific failure mode comes from manual maintainer comments
and third-party automation, not GitHub's own defaults, which is exactly why
nothing catches it after the fact.

## What is ShimGuard, and why does it exist

ShimGuard is a CLI and npm library that checks whether a GitHub issue's
claimed fix ("Fixed in PR #N") is actually true, by checking the real merge
state of that PR (and, optionally, whether the vulnerable code pattern is
still present at `HEAD`). It exists because closing an issue with a citation
to an unmerged PR is a real, observed failure mode, not a hypothetical one:
`sybil-solutions/codex-shim`, a 1,000+-star project, has 6 security issues
closed this way as of this writing, each citing the same unmerged PR #52.
ShimGuard does not scan for secrets in source code (see `gitleaks`,
`trufflehog` for that) and does not do general vulnerability scanning
against dependencies (see `osv-scanner`, `trivy`, `grype`). It verifies one
specific, narrow claim: does a tracker's "fixed" status match reality.

## FAQ

**Does ShimGuard modify my repo or the target repo?**
No. It only makes read-only GitHub API requests (issues, comments, pull
requests, and optionally file contents). It never writes, comments, or
mutates anything.

**Does it need a GitHub token?**
No for occasional use. Unauthenticated requests work, subject to GitHub's
standard rate limit (60 requests/hour). Set `GITHUB_TOKEN` or pass `--token`
for the higher authenticated limit (5,000 requests/hour), useful in CI.

**What counts as a "cited fix"?**
ShimGuard looks for phrases like "Fixed in PR #52", "fixed by #101", or
"resolved in #20" in the issue body and its comments, and extracts the
referenced PR number. If no such phrase is found, the result is
`UNVERIFIED`, not `MATCH` or `MISMATCH`: ShimGuard never guesses.

**Can I use this in CI?**
Yes. `shimguard verify` exits `1` when any MISMATCH is found, so a CI step
can gate on it directly. `--format json` gives a stable, parseable report
for a bot or dashboard.

**Why "ShimGuard" if it doesn't scan BYOK shim configs?**
An earlier framing of this idea was a broader local-config security scanner
for BYOK (bring-your-own-key) model shims. That scope was narrowed to the
sharper, more defensible wedge: verifying tracker claims against actual
merged code, which is what shipped in v0.1. The name reflects the
project's origin case (`sybil-solutions/codex-shim`, a BYOK model shim),
not a scope this version doesn't have.

**Does ShimGuard work on Windows, macOS, and Linux?**
The npm CLI requires Node.js 18 or later (for the built-in `fetch` API) and
runs anywhere Node runs, including Windows, macOS, and Linux. The PyPI
package requires Python 3.9 or later and lists itself as OS Independent in
its own classifiers. Neither package has a native or compiled dependency.

**How is ShimGuard different from gitleaks or trufflehog?**
Gitleaks and trufflehog scan file content for secrets accidentally
committed to a repo, things like API keys and tokens. ShimGuard does not
scan file content for secrets at all -- it checks GitHub's issue and
pull-request API for one specific mismatch: an issue closed as "fixed in
PR #N" where PR #N never actually merged. The two tool categories catch
different failure modes and can run in the same pipeline without
overlapping; see "How it compares" above for the full list of adjacent
tools this project checked before writing a line of code.

**Why does `shimguard --version` print a different number than the
installed package?**
As of npm package `0.1.3`, running `shimguard --version` reports `0.1.2`
-- the version string passed to `commander` in `src/cli.ts` was not
bumped in the `0.1.3` security-fix release. It is a display-only mismatch
and does not affect `verify` behavior. To check the actual installed
version, read the package's own `package.json` or run `npm view
shimguard-cli version`.

**Does ShimGuard scan every closed issue in a repo automatically?**
No. You pass the specific issue numbers to check with `--issues
38,41,42`; ShimGuard does not currently walk a repo's full closed-issue
history looking for cited-fix claims on its own. For a large repo, pick
the issues you care about, for example the ones tagged `security` or tied
to a release milestone.

**Can I use ShimGuard in a commercial product or a paid CI pipeline?**
Yes. ShimGuard is MIT licensed (see [LICENSE](./LICENSE)), which permits
commercial use, modification, and redistribution, including inside a
paid product or internal tool, with no royalty and no requirement to
open-source your own code. Keeping the MIT notice is the only condition.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md).

## Security

See [SECURITY.md](./SECURITY.md).

## License

MIT, see [LICENSE](./LICENSE).

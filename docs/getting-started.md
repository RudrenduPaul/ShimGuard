# Getting started

ShimGuard checks whether a GitHub issue closed as "fixed" actually has a
merged fix, by comparing the tracker's claim (a "Fixed in PR #N" comment)
against the real merge state of PR #N. It ships as two independent, equally
first-class packages: an npm package (`shimguard-cli`, JavaScript/
TypeScript) and a PyPI package (`shimguard-cli`, Python). Pick whichever
fits your toolchain, or install both.

## Install

**npm (JS/TS CLI):**

```bash
npm install -g shimguard-cli
# or run it once without installing:
npx shimguard-cli verify <owner>/<repo> --issues <numbers>
```

**pip (Python library + CLI):**

```bash
pip install shimguard-cli
```

Neither install pulls anything extra at verify time beyond the GitHub REST
API itself: no external binary, no separate toolchain.

## Your first check

Both CLIs point at the same real, documented case: `sybil-solutions/codex-
shim`, where issues #45 and #46 were each closed citing "Fixed in #52", but
PR #52 was never merged.

```bash
# npm CLI
npx shimguard-cli verify sybil-solutions/codex-shim --issues 45,46

# Python CLI (after `pip install shimguard-cli`)
shimguard verify sybil-solutions/codex-shim --issues 45,46
```

Real output (Python CLI shown; the npm CLI's text output is line-for-line
identical):

```
ShimGuard v0.1 -- Tracker Verification: sybil-solutions/codex-shim

[MISMATCH] Issue #45 "_resolve_api_key silently falls back to Cursor API key for any model with an empty api_key, forwarding it to arbitrary upstream URLs"
  https://github.com/sybil-solutions/codex-shim/issues/45
  Cited fix: PR #52 (open, not merged)
  Issue is closed and cites PR #52 as the fix, but that PR is open and was never merged.

[MISMATCH] Issue #46 "_dump_debug_request unconditionally writes full conversation body to a world-readable file in the project directory"
  https://github.com/sybil-solutions/codex-shim/issues/46
  Cited fix: PR #52 (open, not merged)
  Issue is closed and cites PR #52 as the fix, but that PR is open and was never merged.

Summary: 2 MISMATCH, 0 MATCH, 0 UNVERIFIED (2 checked)
```

Exit code `0` means every checked issue's claimed fix actually merged, `1`
means at least one MISMATCH was found, `2` means a usage or network error
(bad repo slug, invalid issue list, GitHub API unreachable).

## Using the library instead of the CLI

Both packages export the verification logic directly for agent frameworks
or CI scripts that want to call ShimGuard in-process instead of shelling out
to a CLI binary.

**TypeScript:**

```ts
import { TrackerVerifier, RestGitHubClient, RegexPatternMatcher } from "shimguard-cli";

const client = new RestGitHubClient(process.env.GITHUB_TOKEN);
const verifier = new TrackerVerifier(client, new RegexPatternMatcher(client));

const result = await verifier.verify({ owner: "sybil-solutions", repo: "codex-shim", number: 45 });
console.log(result.verdict); // "MISMATCH"
```

**Python:**

```python
from shimguard import TrackerVerifier, RestGitHubClient, RegexPatternMatcher, IssueRef

client = RestGitHubClient()  # or RestGitHubClient(token=os.environ["GITHUB_TOKEN"])
verifier = TrackerVerifier(client, RegexPatternMatcher(client))

result = verifier.verify(IssueRef(owner="sybil-solutions", repo="codex-shim", number=45))
print(result.verdict)  # "MISMATCH"
```

Both return the same shape of structured result (`issue`,
`citedPullRequest`/`cited_pull_request`, `patternCheck`/`pattern_check`,
`verdict`, `reason`) -- see [concepts.md](./concepts.md) for the full data
model and the detection heuristic.

## Next steps

- [concepts.md](./concepts.md) -- exactly what counts as a "cited fix," how
  the MATCH/MISMATCH/UNVERIFIED verdict is decided, and what the optional
  code-pattern check adds.
- [integrations/ci.md](./integrations/ci.md) -- wiring ShimGuard into a CI
  pipeline as a gate on tracker hygiene.
- The [project README](../README.md) for the full tool comparison and the
  real `sybil-solutions/codex-shim` case this tool was built from.

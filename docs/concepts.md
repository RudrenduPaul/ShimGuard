# Concepts

## The core check

ShimGuard verifies exactly one claim: **does a GitHub issue's cited "fixed
in PR #N" actually match PR #N's real merge state?** It does this in four
steps, per issue number checked:

1. **Fetch the issue.** If it's still `open`, the verdict is `UNVERIFIED`
   with reason "Issue is still open; no fix has been claimed." -- ShimGuard
   never guesses at an open issue's eventual fix.
2. **Fetch the issue body and all comments**, and search that combined text
   for a fix-reference phrase (see below). If none is found, the verdict is
   `UNVERIFIED` -- the issue is closed, but nothing in it names a specific
   fix PR to check.
3. **Fetch the cited PR.** If `merged` is `false` -- regardless of whether
   the PR is `open` or `closed` -- the verdict is `MISMATCH`. A closed-but-
   unmerged PR is the exact failure mode this tool exists to catch: the PR
   was abandoned or rejected, but the issue still says "fixed."
4. **If the PR is merged**, the verdict is `MATCH`, unless an optional
   `--patterns` code check (below) downgrades it back to `MISMATCH`.

## What counts as a "cited fix"

ShimGuard looks for phrases matching this shape in the issue body and
comments, case-insensitively: a fix keyword (`fixed`, `resolved`, `closed`,
`addressed`), followed by up to 80 characters of anything except a `#`, then
a `#` and a number. Real examples that match: "Fixed in PR #52", "fixed by
#101", "resolved in #20". If multiple references appear across the body and
comments, ShimGuard uses the **last** one found -- closing comments are
usually the most authoritative and tend to come after earlier discussion in
the same thread.

The 80-character bound on the connector text is a deliberate security
constraint, not an arbitrary limit: see [SECURITY.md](../SECURITY.md) for
why an earlier, more permissive version of this regex was vulnerable to
ReDoS (regular expression denial of service) against adversarial issue text
fetched from the target repo.

## Verdicts

| Verdict | Meaning |
| --- | --- |
| `MATCH` | Issue is closed, cites a fix PR, and that PR is genuinely merged (and, if `--patterns` was used, the cited vulnerable code is confirmed gone from `HEAD`). |
| `MISMATCH` | Issue is closed and cites a fix PR, but that PR was never merged -- or it was merged and the cited vulnerable pattern is still present at `HEAD`. |
| `UNVERIFIED` | Issue is still open, or is closed but names no specific fix PR to check. Not a judgment either way -- ShimGuard has nothing concrete to verify. |

## Optional: the code-pattern check

`--patterns` accepts a JSON file mapping issue numbers to a `{path,
pattern}` pair. When the cited PR is merged, ShimGuard additionally fetches
`path` at `HEAD` and tests whether `pattern` (a regular expression) still
matches its content:

- **Pattern found** -- the merged PR did not actually remove the vulnerable
  line. Verdict downgrades from `MATCH` to `MISMATCH`, with a reason citing
  the specific file.
- **Pattern absent** -- confirms the fix. Verdict stays `MATCH`.
- **Inconclusive** (file not found at `HEAD`, fetch error, oversized file,
  or the match itself timed out) -- the merge-state check already passed,
  so the verdict stays `MATCH`, but the reason notes the pattern check could
  not confirm anything either way.

This is the strongest available check, because a merged PR alone only
proves *something* was merged under that PR number -- not that it actually
removed the specific vulnerable code the issue described.

**Trust boundary:** `pattern` is compiled as a real regular expression
(`RegExp` in the npm CLI, Python's `re` module in the Python CLI) and
matched against file content fetched live from the target repo, which by
this tool's own purpose may not be a repo you fully trust. Only point
`--patterns` at files you wrote or reviewed yourself. Both implementations
run the match under a hard timeout in an isolated worker (a Node worker
thread in the npm CLI, a subprocess in the Python CLI) specifically to bound
worst-case time against a pathological pattern/content combination -- see
[SECURITY.md](../SECURITY.md).

## Output formats

`--format text` (default) is meant for a human reading a terminal: one block
per issue, then a one-line summary. `--format json` is a stable, versioned
contract meant for scripts and AI agents to parse directly -- the same
`{repo, checked, summary, results}` shape and the same field names
(`citedPullRequest`, `patternCheck`, `htmlUrl`, etc.) on both the npm and
Python CLIs, so a pipeline can swap one for the other without changing its
parsing code.

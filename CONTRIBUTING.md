# Contributing to ShimGuard

Thanks for considering a contribution. ShimGuard ships two independently
maintained, equally first-class distributions of the same verification
logic: an npm package (`shimguard-cli`, TypeScript, repo root) and a PyPI
package (`shimguard-cli`, Python, `python/`). Both implement the same
"closed issue cites Fixed in PR #N, is #N actually merged" check against
the live GitHub REST API and are expected to produce the same verdict
against the same target. Please read the section for whichever codebase
you're touching.

## Ground rules

- Every change lands with tests. Neither test suite is optional scaffolding
  -- both are the mechanism that keeps the two implementations in parity.
- A change to the fix-reference regex, the verdict logic, or the pattern-
  matcher's ReDoS guard should land in **both** `src/` (TypeScript) and
  `python/src/shimguard/` (Python), with equivalent test coverage added to
  both suites. A behavior change that only exists in one language is a
  silent gap between the two CLIs -- avoid it.
- Output format (`--format text`/`--format json`), field names, and exit
  codes (0 clean, 1 MISMATCH found, 2 usage/network error) should read
  identically between the two CLIs. If you intentionally diverge them, say
  so explicitly in the PR description.
- No `eval`/`exec`/dynamic `require`/`import` of anything read from the
  target repo being audited, in either codebase. ShimGuard's entire premise
  is that it's safe to run against a repo you don't fully trust; a change
  that breaks that invariant is not a fix.

## Working on the TypeScript package (repo root)

```bash
git clone https://github.com/RudrenduPaul/ShimGuard.git
cd ShimGuard
npm install
npm run build
npm test
```

Run the full check suite locally, the same one CI runs, before opening a PR:

```bash
npm run lint
npm run typecheck
npm run build
npm run test:coverage
npm audit --audit-level=high
```

All four must pass. Coverage thresholds (80% lines/statements/functions,
75% branches) are enforced in CI.

## Working on the Python package (`python/`)

```bash
cd python
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

- Source lives under `python/src/shimguard/`, laid out to mirror the
  TypeScript module structure (`types.py`, `github.py`, `pattern_matcher.py`,
  `verifier.py`, `cli_lib.py`, `cli.py`) so a change in one codebase has an
  obvious counterpart to check in the other.
- The Python `RegexPatternMatcher` enforces its ReDoS timeout with a
  `multiprocessing.Process` instead of the TypeScript version's worker
  thread (Python threads can't be force-killed out of a C-level regex
  loop; a subprocess can be sent a real `SIGTERM`) -- same guarantee,
  different mechanism. Keep this in mind if you change the timeout value in
  one implementation; change both.
- Build and verify a real install before opening a PR that touches
  packaging:
  ```bash
  python3 -m build python --outdir /tmp/shimguard-dist
  python3 -m venv /tmp/sg-verify && /tmp/sg-verify/bin/pip install /tmp/shimguard-dist/*.whl
  /tmp/sg-verify/bin/shimguard verify sybil-solutions/codex-shim --issues 45
  ```

## Adding a new fix-reference pattern

`extractFixReference` (`src/verifier.ts`) / `extract_fix_reference`
(`python/src/shimguard/verifier.py`) recognizes phrases like "Fixed in PR
#52" or "resolved by #101". If you find a real-world closing comment
phrasing it misses, add a fixture case to both test suites first, then
extend the regex to match in both languages. Keep the regex free of nested
quantifiers that could cause catastrophic backtracking -- the current
`{0,80}` bounded connector class is deliberate (see
[SECURITY.md](./SECURITY.md)), don't reintroduce chained optional/greedy
groups.

## Adding a new PatternMatcher

The `PatternMatcher` interface (`src/pattern-matcher.ts` /
`python/src/shimguard/pattern_matcher.py`) is the extension point for future
verification strategies (a local shim-config scanner, a different code-
hosting API). Implement the interface, add real fixture-based tests, and
wire it in via `TrackerVerifier`'s constructor rather than adding
special-case branches to `TrackerVerifier` itself.

## Reporting a bug

Open a GitHub issue with the exact `shimguard verify` command you ran
(state which distribution -- npm or pip), the repo/issue numbers involved,
and the actual vs. expected output. If it's a security issue, see
[SECURITY.md](./SECURITY.md) instead.

## License

By contributing, you agree your contribution is licensed under the same MIT
License that covers the rest of this repository (see [LICENSE](./LICENSE)).

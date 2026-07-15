# Contributing to ShimGuard

Thanks for considering a contribution.

## Development setup

```bash
git clone https://github.com/RudrenduPaul/ShimGuard.git
cd ShimGuard
npm install
npm run build
npm test
```

## Before opening a PR

Run the full check suite locally, the same one CI runs:

```bash
npm run lint
npm run typecheck
npm run build
npm run test:coverage
npm audit --audit-level=high
```

All four must pass. Coverage thresholds (80% lines/statements/functions,
75% branches) are enforced in CI.

## Adding a new fix-reference pattern

`extractFixReference` in `src/verifier.ts` recognizes phrases like "Fixed in
PR #52" or "resolved by #101". If you find a real-world closing comment
phrasing it misses, add a fixture case to `test/verifier.test.ts` first,
then extend the regex to match. Keep the regex free of nested quantifiers
that could cause catastrophic backtracking.

## Adding a new PatternMatcher

The `PatternMatcher` interface (`src/pattern-matcher.ts`) is the extension
point for future verification strategies (a local shim-config scanner, a
different code-hosting API). Implement the interface, add real fixture-based
tests, and wire it in via `TrackerVerifier`'s constructor rather than adding
special-case branches to `TrackerVerifier` itself.

## Reporting a bug

Open a GitHub issue with the exact `shimguard verify` command you ran, the
repo/issue numbers involved, and the actual vs. expected output. If it's a
security issue, see [SECURITY.md](./SECURITY.md) instead.

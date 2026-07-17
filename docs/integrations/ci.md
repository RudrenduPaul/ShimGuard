# CI integrations

ShimGuard is meant to run as a periodic or on-demand check against your own
tracker, not on every commit -- it audits closed issues, not new code. Both
packages support the same `--issues`/`--patterns`/`--format` contract and
the same exit-code convention (`0` clean, `1` MISMATCH found, `2` error), so
pick whichever matches your pipeline's existing toolchain. **Honest note:**
unlike some sibling tools in this account, ShimGuard does not currently ship
a bundled composite GitHub Action -- both examples below are plain CI steps.

## GitHub Actions -- npm CLI

```yaml
name: ShimGuard tracker audit
on:
  schedule:
    - cron: '0 6 * * 1'  # weekly
  workflow_dispatch:

jobs:
  shimguard:
    runs-on: ubuntu-latest
    steps:
      - name: Run ShimGuard
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          npx --yes shimguard-cli verify your-org/your-repo \
            --issues 101,102,103 --format json > shimguard-results.json
      - name: Fail on MISMATCH
        run: |
          if [ $? -eq 1 ]; then
            echo "ShimGuard found a closed issue whose cited fix PR never merged."
            exit 1
          fi
```

## GitHub Actions -- Python CLI

```yaml
name: ShimGuard tracker audit (Python)
on:
  schedule:
    - cron: '0 6 * * 1'
  workflow_dispatch:

jobs:
  shimguard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install shimguard-cli
      - name: Run ShimGuard
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          shimguard verify your-org/your-repo --issues 101,102,103 --format json \
            > shimguard-results.json
```

(Both CLIs read `GITHUB_TOKEN` from the environment automatically when
`--token` isn't passed explicitly; the built-in `GITHUB_TOKEN` GitHub
Actions provides is sufficient to raise the rate limit from 60 to 5,000
requests/hour.)

## Why a scheduled check, not a per-commit gate

Nothing about a new commit changes whether an *old*, already-closed issue's
cited fix PR is merged -- that state only changes when someone merges (or
fails to merge) the cited PR itself. A weekly or on-demand scheduled run
against your tracker's recently-closed issues is the natural cadence; wiring
ShimGuard into a pre-merge PR gate would just re-check the same unchanged
issues on every unrelated commit.

## Choosing which issues to check

ShimGuard takes an explicit `--issues` list rather than scanning an entire
tracker, by design: fetching every closed issue in a large repo's history on
every run would be slow and mostly redundant (once an issue is verified
`MATCH`, its citied PR's merge state does not change). A practical pattern
is to track a small, curated list of security-sensitive issue numbers (or
recently-closed issues from the last audit window) rather than the whole
tracker.

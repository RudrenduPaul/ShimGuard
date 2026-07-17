# Python examples

Each numbered subdirectory is a real, runnable script against the actual
`shimguard` Python library (`from shimguard import TrackerVerifier, ...`),
not pseudocode. Examples 01 and 02 make real, live GitHub API calls against
the real `sybil-solutions/codex-shim` repo (the documented case ShimGuard
was built from -- see the project README); example 03 does the same for its
first part, then uses a small in-memory client for its second part (clearly
labeled in the script).

Install the package first (editable install from this checkout, or `pip
install shimguard-cli` from PyPI both work identically):

```bash
cd python
pip install -e .
```

Then run any example directly:

```bash
python3 examples/01-basic-verify/verify.py
python3 examples/02-ci-gate/gate.py
python3 examples/03-pattern-check/pattern_check.py
```

| Example | What it demonstrates |
| --- | --- |
| [01-basic-verify](./01-basic-verify/) | The core library call: build a `TrackerVerifier`, call `verify()`, read back `verdict`/`reason`/`cited_pull_request` -- against the real, live `sybil-solutions/codex-shim#45` and `#46`. |
| [02-ci-gate](./02-ci-gate/) | Using `TrackerVerifier` as a CI gate: repo/issue list from the command line, real process exit-code propagation (0 pass / 1 fail / 2 error), suitable to drop into a scheduled CI job directly. |
| [03-pattern-check](./03-pattern-check/) | The optional `--patterns` code check: real short-circuit behavior when the merge check alone already resolves to MISMATCH, plus a synthetic in-memory example of the MATCH-to-MISMATCH downgrade when a merged PR leaves the cited vulnerable pattern in place. |

An unauthenticated GitHub API call is limited to 60 requests/hour; set
`GITHUB_TOKEN` in your environment before running the examples repeatedly to
raise that to 5,000/hour. `RestGitHubClient` itself never reads the
environment implicitly (only the `shimguard` CLI does, as its `--token`
default) -- each example passes `token=os.environ.get("GITHUB_TOKEN")`
explicitly, which is the pattern to follow in your own code too.

"""
Ported from src/pattern-matcher.ts (RegexPatternMatcher). Same threat model
and same defense: the operator's --patterns regex is matched against file
content fetched live from the target repo, which by this tool's own purpose
may be untrusted, so an ordinary-looking regex (e.g. "(\\w+\\s*)+$") can
still hang indefinitely via catastrophic backtracking against adversarial
content.

The TypeScript version runs the match in a worker thread with a hard
deadline and terminates it on timeout. Python's `re` module has no native
match timeout and, unlike Node worker threads, a Python *thread* cannot be
force-killed once it is inside a C-level regex loop -- so this port runs the
match in a subprocess instead: `multiprocessing.Process.terminate()` sends a
real SIGTERM the OS enforces, giving the same "abort a hung match" guarantee
the TypeScript version gets from worker.terminate().
"""
from __future__ import annotations

import multiprocessing
import re
from typing import Optional, Protocol, Tuple, runtime_checkable

from .types import GitHubClient, PatternCheck

MAX_CONTENT_BYTES = 1_000_000
REGEX_TIMEOUT_SECONDS = 2.0


@runtime_checkable
class PatternMatcher(Protocol):
    def check(
        self, owner: str, repo: str, path: str, pattern: str, ref: str = "HEAD"
    ) -> PatternCheck: ...


def _match_worker(pattern: str, content: str, queue: "multiprocessing.Queue") -> None:
    try:
        found = re.search(pattern, content) is not None
    except re.error:
        queue.put(("error", "invalid-regex"))
        return
    except Exception:  # noqa: BLE001 -- mirrors the TS worker's catch-all
        queue.put(("error", "worker-error"))
        return
    queue.put(("found", found))


def _run_regex_with_timeout(pattern: str, content: str, timeout_s: float) -> Tuple[str, object]:
    ctx = multiprocessing.get_context("spawn")
    queue: "multiprocessing.Queue" = ctx.Queue()
    proc = ctx.Process(target=_match_worker, args=(pattern, content, queue), daemon=True)
    proc.start()
    proc.join(timeout_s)

    if proc.is_alive():
        proc.terminate()
        proc.join(1.0)
        if proc.is_alive():
            proc.kill()
            proc.join()
        return ("timed_out", None)

    if not queue.empty():
        return queue.get()
    # Process exited without putting a result (e.g. killed by the OS OOM
    # killer) -- treat the same as an unexpected worker failure.
    return ("error", "worker-error")


class RegexPatternMatcher:
    def __init__(self, client: GitHubClient) -> None:
        self.client = client

    def check(
        self, owner: str, repo: str, path: str, pattern: str, ref: str = "HEAD"
    ) -> PatternCheck:
        try:
            content: Optional[str] = self.client.get_file_content(owner, repo, path, ref)
        except Exception as err:  # noqa: BLE001 -- mirrors the TS try/catch around the fetch
            return PatternCheck(path=path, pattern=pattern, found=None, note=f"Could not fetch {path}: {err}")

        if content is None:
            return PatternCheck(path=path, pattern=pattern, found=None, note=f"{path} not found at {ref}")

        if len(content.encode("utf-8")) > MAX_CONTENT_BYTES:
            return PatternCheck(
                path=path,
                pattern=pattern,
                found=None,
                note=f"{path} is larger than {MAX_CONTENT_BYTES} bytes at {ref}; skipped to bound matching cost",
            )

        kind, payload = _run_regex_with_timeout(pattern, content, REGEX_TIMEOUT_SECONDS)

        if kind == "timed_out":
            return PatternCheck(
                path=path,
                pattern=pattern,
                found=None,
                note=(
                    f"Pattern match against {path} exceeded {int(REGEX_TIMEOUT_SECONDS * 1000)}ms "
                    "and was aborted (likely catastrophic regex backtracking)"
                ),
            )
        if kind == "error":
            note = (
                f"Invalid pattern regex: {pattern}"
                if payload == "invalid-regex"
                else f"Pattern match against {path} failed unexpectedly"
            )
            return PatternCheck(path=path, pattern=pattern, found=None, note=note)

        return PatternCheck(path=path, pattern=pattern, found=bool(payload))

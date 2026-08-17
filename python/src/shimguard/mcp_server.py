"""MCP server for shimguard: a single generic `run` tool that shells out to
the installed `shimguard` CLI, so an MCP-compatible agent can invoke any
shimguard subcommand (currently just `verify`) without a bespoke tool per
subcommand. Requires the `mcp` extra (`pip install "shimguard-cli[mcp]"`).
Started via `shimguard-mcp` (stdio transport).

Uses `mcp.server.MCPServer`, the official SDK's current high-level server
class (`mcp` 2.0.0+); earlier 1.x releases exposed the same `.tool()`/
`.run()` pattern under the now-removed `mcp.server.fastmcp.FastMCP`.

Every tool handler here is wrapped so it cannot raise: subprocess launch
failures (OSError), timeouts, non-zero exit codes, and non-JSON stdout are
all converted into a returned `{"error": ...}` dict instead of an
exception, since an MCP tool that raises breaks the calling agent's turn.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

from mcp.server import MCPServer

_CLI_BIN = shutil.which("shimguard") or "shimguard"
_TIMEOUT_SECONDS = 120

_TOOL_DESCRIPTION = (
    "Runs shimguard's 'verify' check against a public GitHub repo and returns whether each "
    "issue the repo's tracker claims is 'fixed' actually has a merged pull request behind "
    "it. Call this when you need to trust a tracker's closed-issue state before relying on "
    "it -- e.g. before telling a user a security bug is patched, before citing an issue as "
    "resolved in a report, or while triaging which of several 'closed' issues are still "
    "live because their cited fix PR never merged. Do not call it for open issues (there is "
    "nothing to verify yet) or for repos you don't have read access to.\n\n"
    "Prerequisites: the `shimguard` binary must be on PATH (bundled with this package); no "
    "auth is required for public repos at GitHub's unauthenticated rate limit, but for "
    "private repos or to avoid rate-limiting on repeated calls, set $GITHUB_TOKEN or pass "
    "'--token <token>'.\n\n"
    "This tool is strictly read-only: it makes outbound HTTPS calls to the GitHub REST API "
    "(one per issue, plus one per cited pull request) and writes nothing anywhere, locally "
    "or on GitHub. Results are not cached and can change between calls if the repo's issue "
    "or PR state changes, so it is safe and meaningful to re-run. The underlying CLI exits "
    "0 when every checked issue's claimed fix actually merged, 1 when any MISMATCH is "
    "found, and 2 on a usage or network error -- this wrapper never raises regardless: a "
    "missing binary, launch failure, timeout, or non-zero exit is always returned as "
    "{\"error\": ...} alongside the raw returncode/stdout/stderr, never an exception.\n\n"
    "Parameter `args` is the literal argv you would type after `shimguard` on the command "
    "line, as a list of strings. Real examples: run(args=[\"verify\", "
    "\"sybil-solutions/codex-shim\", \"--issues\", \"38,41,42\", \"--format\", \"json\"]) to "
    "check three specific closed issues; run(args=[\"verify\", \"owner/repo\", \"--format\", "
    "\"json\"]) to check every closed issue in the repo; run(args=[\"verify\", "
    "\"owner/repo\", \"--issues\", \"45,46\", \"--patterns\", \"./patterns.json\", "
    "\"--format\", \"json\"]) to additionally confirm the fix pattern actually appears in "
    "the merged code, using a JSON file mapping issue number to {path, pattern}. Always "
    "include '--format json' -- without it the CLI prints human-readable text instead of a "
    "parseable object.\n\n"
    "Returns {\"returncode\", \"stdout\", \"stderr\"} plus a parsed \"json\" key when stdout "
    "was valid JSON (only when '--format json' was passed). That JSON has the shape "
    "{\"repo\", \"checked\", \"summary\": {\"mismatch\", \"match\", \"unverified\"}, "
    "\"results\": [{\"issue\": {...}, \"citedPullRequest\": {...}, \"patternCheck\", "
    "\"verdict\", \"reason\"}]}. Pass run(args=[\"--help\"]) or run(args=[\"verify\", "
    "\"--help\"]) for the CLI's own current usage text."
)

mcp = MCPServer("shimguard")


@mcp.tool(description=_TOOL_DESCRIPTION)
def run(args: list[str]) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            [_CLI_BIN, *args],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SECONDS,
        )
    except OSError as exc:
        return {"error": f"failed to launch the shimguard CLI: {exc}"}
    except subprocess.TimeoutExpired:
        return {"error": f"shimguard CLI timed out after {_TIMEOUT_SECONDS}s"}

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""

    if proc.returncode != 0:
        return {
            "error": stderr.strip() or stdout.strip() or f"shimguard exited with code {proc.returncode}",
            "returncode": proc.returncode,
            "stdout": stdout,
            "stderr": stderr,
        }

    result: dict[str, Any] = {
        "returncode": proc.returncode,
        "stdout": stdout,
        "stderr": stderr,
    }
    if stdout.strip():
        try:
            result["json"] = json.loads(stdout)
        except json.JSONDecodeError:
            pass  # stdout wasn't JSON (e.g. --format json wasn't passed); text is still in "stdout"
    return result


def main() -> None:
    """Entry point for the `shimguard-mcp` console script."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

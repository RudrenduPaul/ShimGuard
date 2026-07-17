"""
Ported from src/cli-lib.ts: repo-slug/issue-list parsing, the --patterns
JSON loader, verdict summarizing, and the two output formatters (text and
JSON). Kept as free functions, same as the TypeScript module, so the CLI
layer (cli.py) stays a thin wrapper and the library API can format results
independently of argparse.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Tuple

from .types import VerificationResult
from .verifier import PatternSpec

PatternsFile = Dict[str, PatternSpec]


def parse_repo_slug(slug: str) -> Tuple[str, str]:
    parts = slug.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f'Invalid repo "{slug}". Expected "<owner>/<repo>".')
    return parts[0], parts[1]


def parse_issue_list(raw: str) -> List[int]:
    pieces = [s.strip() for s in raw.split(",") if s.strip()]
    nums: List[int] = []
    for piece in pieces:
        try:
            nums.append(int(piece))
        except ValueError:
            nums = []
            break
    if not nums or any(n <= 0 for n in nums):
        raise ValueError(
            f'Invalid --issues value "{raw}". Expected a comma-separated list of positive integers.'
        )
    return nums


def load_patterns(path: str | None) -> PatternsFile:
    if not path:
        return {}
    raw = Path(path).read_text(encoding="utf-8")
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError(f'--patterns file "{path}" must contain a JSON object.')
    return {
        str(key): PatternSpec(path=value["path"], pattern=value["pattern"])
        for key, value in parsed.items()
    }


def summarize(results: List[VerificationResult]) -> Dict[str, int]:
    return {
        "mismatch": sum(1 for r in results if r.verdict == "MISMATCH"),
        "match": sum(1 for r in results if r.verdict == "MATCH"),
        "unverified": sum(1 for r in results if r.verdict == "UNVERIFIED"),
    }


_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def _sanitize_for_text(s: str) -> str:
    """Strip control characters (ANSI escapes, terminal OSC sequences,
    embedded newlines) from issue-tracker text -- comes from the (possibly
    untrusted) audited repo -- before writing it into text output that may
    be piped into a terminal or a CI summary."""
    return _CONTROL_CHARS.sub("", s)


def format_text(results: List[VerificationResult], repo_slug: str) -> str:
    lines = [f"ShimGuard v0.1 -- Tracker Verification: {repo_slug}", ""]
    for r in results:
        label = {"MISMATCH": "MISMATCH", "MATCH": "MATCH   "}.get(r.verdict, "UNKNOWN ")
        lines.append(f'[{label}] Issue #{r.issue.number} "{_sanitize_for_text(r.issue.title)}"')
        lines.append(f"  {r.issue.html_url}")
        if r.cited_pull_request:
            merge_state = "merged" if r.cited_pull_request.merged else f"{r.cited_pull_request.state}, not merged"
            lines.append(f"  Cited fix: PR #{r.cited_pull_request.number} ({merge_state})")
        if r.pattern_check:
            if r.pattern_check.found is None:
                status = "inconclusive"
            elif r.pattern_check.found:
                status = "still present"
            else:
                status = "absent"
            lines.append(f"  Pattern check ({r.pattern_check.path}): {status}")
        lines.append(f"  {r.reason}")
        lines.append("")
    summary = summarize(results)
    lines.append(
        f"Summary: {summary['mismatch']} MISMATCH, {summary['match']} MATCH, "
        f"{summary['unverified']} UNVERIFIED ({len(results)} checked)"
    )
    return "\n".join(lines)


def _result_to_dict(result: VerificationResult) -> dict:
    # Field names are deliberately camelCase (htmlUrl, patternCheck, ...) to
    # match src/cli-lib.ts's formatJson() byte-for-byte, since --format json
    # is a stable contract scripts and agents parse against either CLI.
    issue = {
        "number": result.issue.number,
        "title": result.issue.title,
        "state": result.issue.state,
        "htmlUrl": result.issue.html_url,
    }
    cited_pr = None
    if result.cited_pull_request:
        cited_pr = {
            "number": result.cited_pull_request.number,
            "state": result.cited_pull_request.state,
            "merged": result.cited_pull_request.merged,
            "htmlUrl": result.cited_pull_request.html_url,
        }
    pattern_check = asdict(result.pattern_check) if result.pattern_check else None
    return {
        "issue": issue,
        "citedPullRequest": cited_pr,
        "patternCheck": pattern_check,
        "verdict": result.verdict,
        "reason": result.reason,
    }


def format_json(results: List[VerificationResult], repo_slug: str) -> str:
    summary = summarize(results)
    payload = {
        "repo": repo_slug,
        "checked": len(results),
        "summary": summary,
        "results": [_result_to_dict(r) for r in results],
    }
    return json.dumps(payload, indent=2)

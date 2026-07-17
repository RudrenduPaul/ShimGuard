#!/usr/bin/env python3
"""
Thin argument-parsing wrapper over TrackerVerifier (see verifier.py for the
actual detection logic). Ported from src/cli.ts, which uses `commander`;
this port uses the stdlib `argparse` to avoid a CLI-framework dependency
(same choice the skillguard-cli Python port made). Console entry point:
`shimguard verify <owner>/<repo> --issues <numbers>`, installed via the
`shimguard` console-script defined in python/pyproject.toml.

Exit codes match the TypeScript CLI exactly: 0 clean, 1 any MISMATCH found,
2 usage/network error.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import List

from .cli_lib import format_json, format_text, load_patterns, parse_issue_list, parse_repo_slug
from .github import GitHubApiError, RestGitHubClient
from .pattern_matcher import RegexPatternMatcher
from .types import IssueRef, VerificationResult
from .verifier import TrackerVerifier

__version__ = "0.1.0"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shimguard",
        description=(
            'Verify that GitHub issues closed as "fixed" actually have a merged fix. '
            "Catches security issues marked fixed whose PR was never merged."
        ),
    )
    parser.add_argument("--version", action="version", version=f"shimguard-cli {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    verify_parser = subparsers.add_parser(
        "verify", help="Check whether closed issues in a repo actually have a merged fix"
    )
    verify_parser.add_argument("repo", help="target repo as <owner>/<repo>, e.g. sybil-solutions/codex-shim")
    verify_parser.add_argument(
        "--issues", required=True, help="comma-separated issue numbers to check, e.g. 38,41,42"
    )
    verify_parser.add_argument(
        "--patterns",
        default=None,
        help="JSON file mapping issue number -> {path, pattern} for an optional code-pattern check",
    )
    verify_parser.add_argument(
        "--token", default=None, help="GitHub token for higher API rate limits (defaults to $GITHUB_TOKEN)"
    )
    verify_parser.add_argument(
        "--format", default="text", help='output format: "text" or "json" (default: "text")'
    )

    return parser


def _run_verify(args: argparse.Namespace) -> int:
    if args.format not in ("text", "json"):
        raise ValueError(f'Invalid --format "{args.format}". Expected "text" or "json".')

    owner, repo = parse_repo_slug(args.repo)
    issue_numbers = parse_issue_list(args.issues)
    patterns = load_patterns(args.patterns)
    token = args.token or os.environ.get("GITHUB_TOKEN")

    client = RestGitHubClient(token)
    matcher = RegexPatternMatcher(client)
    verifier = TrackerVerifier(client, matcher)

    results: List[VerificationResult] = []
    for number in issue_numbers:
        spec = patterns.get(str(number))
        results.append(verifier.verify(IssueRef(owner=owner, repo=repo, number=number), spec))

    output = format_json(results, args.repo) if args.format == "json" else format_text(results, args.repo)
    print(output)

    return 1 if any(r.verdict == "MISMATCH" for r in results) else 0


def run_cli(argv: List[str]) -> int:
    """`argv` follows the sys.argv convention: argv[0] is the program name."""
    parser = build_parser()
    args = parser.parse_args(argv[1:])

    if args.command != "verify":
        parser.print_help()
        return 0

    try:
        return _run_verify(args)
    except GitHubApiError as err:
        print(f"Error: {err}", file=sys.stderr)
        return 2
    except (ValueError, OSError) as err:
        print(f"Error: {err}", file=sys.stderr)
        return 2


def main() -> None:
    sys.exit(run_cli(sys.argv))


if __name__ == "__main__":
    main()

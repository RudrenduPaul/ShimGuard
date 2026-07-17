"""Ported from test/cli.test.ts. The TS suite shells out to the built
dist/cli.js; this port exercises run_cli() directly for the fast unit cases
(matching argparse's own exit-code contract) plus a real subprocess
invocation via `python -m shimguard.cli` for the two smoke tests (--help,
--version), the same "run the actual installed entry point" style the TS
suite uses."""
from __future__ import annotations

import subprocess
import sys

import pytest

from shimguard.cli import __version__, run_cli


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "shimguard.cli", *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


class TestCliSubprocess:
    def test_help_lists_verify_subcommand(self) -> None:
        result = _run(["--help"])
        assert result.returncode == 0
        assert "verify" in result.stdout
        assert "shimguard" in result.stdout

    def test_prints_version(self) -> None:
        result = _run(["--version"])
        assert result.returncode == 0
        assert result.stdout.strip() == f"shimguard-cli {__version__}"


class TestCliInProcess:
    def test_exits_2_on_invalid_repo_slug(self, capsys: pytest.CaptureFixture[str]) -> None:
        code = run_cli(["shimguard", "verify", "not-a-valid-slug", "--issues", "1"])
        captured = capsys.readouterr()
        assert code == 2
        assert captured.out == ""
        assert "Error:" in captured.err

    def test_exits_2_on_invalid_issues_value(self, capsys: pytest.CaptureFixture[str]) -> None:
        code = run_cli(["shimguard", "verify", "owner/repo", "--issues", "not-a-number"])
        captured = capsys.readouterr()
        assert code == 2
        assert captured.out == ""
        assert "Error:" in captured.err

    def test_exits_2_on_invalid_format(self, capsys: pytest.CaptureFixture[str]) -> None:
        code = run_cli(["shimguard", "verify", "owner/repo", "--issues", "1", "--format", "yaml"])
        captured = capsys.readouterr()
        assert code == 2
        assert "Error:" in captured.err

    def test_no_command_prints_help_and_exits_0(self, capsys: pytest.CaptureFixture[str]) -> None:
        code = run_cli(["shimguard"])
        assert code == 0

"""
Programmatic / agent-native entry point.

    from shimguard import TrackerVerifier, RestGitHubClient, RegexPatternMatcher, IssueRef

    client = RestGitHubClient(token=os.environ.get("GITHUB_TOKEN"))
    verifier = TrackerVerifier(client, RegexPatternMatcher(client))
    result = verifier.verify(IssueRef(owner="sybil-solutions", repo="codex-shim", number=45))
    print(result.verdict)  # "MISMATCH"

This is the Python port of the shimguard-cli npm package
(https://www.npmjs.com/package/shimguard-cli). Both distributions implement
the same "closed issue cites Fixed in PR #N, is #N actually merged" check
against the live GitHub REST API; see
https://github.com/RudrenduPaul/ShimGuard for the canonical documentation
and the original TypeScript source.
"""
from importlib import metadata as _importlib_metadata

from .github import GitHubApiError, RestGitHubClient
from .pattern_matcher import PatternMatcher, RegexPatternMatcher
from .types import (
    GitHubClient,
    GitHubComment,
    GitHubIssue,
    GitHubPullRequest,
    IssueRef,
    IssueSummary,
    PatternCheck,
    PullRequestSummary,
    Verdict,
    VerificationResult,
)
from .verifier import PatternSpec, TrackerVerifier, extract_fix_reference

try:
    # Read the version from the installed package's own metadata rather than
    # a hand-maintained string here, which silently drifted from the real
    # pyproject.toml version (this constant, and cli.py's separate __version__
    # constant, were still "0.1.0" while the package had shipped 0.1.3 on
    # PyPI, so `shimguard --version` reported a stale, wrong version to
    # every user and agent that checked it).
    __version__ = _importlib_metadata.version("shimguard-cli")
except _importlib_metadata.PackageNotFoundError:
    # Not installed (e.g. running straight from a source checkout without
    # `pip install -e .`) -- fall back to a clearly-labeled placeholder
    # instead of a number that can silently go stale again.
    __version__ = "0.0.0-dev"

__all__ = [
    "TrackerVerifier",
    "extract_fix_reference",
    "PatternSpec",
    "RegexPatternMatcher",
    "PatternMatcher",
    "RestGitHubClient",
    "GitHubApiError",
    "GitHubClient",
    "GitHubIssue",
    "GitHubComment",
    "GitHubPullRequest",
    "IssueRef",
    "IssueSummary",
    "PullRequestSummary",
    "PatternCheck",
    "VerificationResult",
    "Verdict",
    "__version__",
]

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

__version__ = "0.1.0"

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

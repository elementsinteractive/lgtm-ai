import binascii
import logging
from functools import lru_cache
from urllib.parse import urlparse

import github
import github.ContentFile
import github.File
import github.GithubException
import github.PullRequest
import github.PullRequestReview
import github.Repository
from lgtm_ai.ai.schemas import Review, ReviewGuide
from lgtm_ai.base.schemas import PRUrl
from lgtm_ai.formatters.base import Formatter
from lgtm_ai.git_client.base import GitClient
from lgtm_ai.git_client.exceptions import (
    PublishGuideError,
    PublishReviewError,
    PullRequestDiffError,
    PullRequestMetadataError,
)
from lgtm_ai.git_client.schemas import ContextBranch, IssueContent, PRDiff, PRMetadata
from lgtm_ai.git_parser.exceptions import GitDiffParseError
from lgtm_ai.git_parser.parser import DiffFileMetadata, DiffResult, parse_diff_patch
from pydantic import HttpUrl

logger = logging.getLogger("lgtm.git")


class GitHubClient(GitClient):
    def __init__(self, client: github.Github, formatter: Formatter[str]) -> None:
        self.client = client
        self.formatter = formatter

    def get_diff_from_url(self, pr_url: PRUrl) -> PRDiff:
        """Return a PRDiff object containing an identifier to the diff and a stringified representation of the diff from the latest version of the given pull request URL."""
        logger.info("Fetching diff from GitHub")

        try:
            pr = _get_pr(self.client, pr_url)
            files = pr.get_files()
        except github.GithubException as err:
            logger.error("Failed to retrieve the diff of the pull request")
            raise PullRequestDiffError from err

        parsed: list[DiffResult] = []
        for file in files:
            metadata = DiffFileMetadata(
                new_file=(file.status == "added"),
                deleted_file=(file.status == "removed"),
                renamed_file=(file.status == "renamed"),
                new_path=file.filename,
                old_path=getattr(file, "previous_filename", None),
            )
            try:
                parsed_diff = parse_diff_patch(metadata=metadata, diff_text=file.patch)
            except GitDiffParseError:
                logger.exception("Failed to parse diff patch, will skip it")
                continue
            parsed.append(parsed_diff)

        return PRDiff(
            id=pr.number,
            diff=parsed,
            changed_files=[file.filename for file in files],
            target_branch=pr.base.ref,
            source_branch=pr.head.ref,
        )

    def publish_review(self, pr_url: PRUrl, review: Review) -> None:
        """Publish the review to the given pull request URL.

        Publish a main summary comment and then specific line comments.
        """
        pr = _get_pr(self.client, pr_url)
        # Prepare the list of inline comments
        comments: list[github.PullRequest.ReviewComment] = []
        for c in review.review_response.comments:
            comments.append(
                {
                    "path": c.new_path,
                    "position": c.relative_line_number,
                    "body": self.formatter.format_review_comment(c),
                }
            )
        try:
            commit = pr.base.repo.get_commit(pr.head.sha)
            pr.create_review(
                body=self.formatter.format_review_summary_section(review),
                event="COMMENT",
                comments=comments,
                commit=commit,
            )
        except github.GithubException as err:
            raise PublishReviewError from err

    def get_pr_metadata(self, pr_url: PRUrl) -> PRMetadata:
        """Return a PRMetadata object containing the metadata of the given pull request URL."""
        try:
            pr = _get_pr(self.client, pr_url)
        except github.GithubException as err:
            logger.error("Failed to retrieve the metadata of the pull request")
            raise PullRequestMetadataError from err

        return PRMetadata(title=pr.title or "", description=pr.body or "")

    def get_issue_content(self, issues_url: HttpUrl, issue_id: str) -> IssueContent | None:
        try:
            repo = _get_repo_from_issues_url(self.client, issues_url)
            issue = repo.get_issue(int(issue_id))
        except (github.GithubException, ValueError) as err:
            logger.error("Failed to retrieve the issue content from GitHub for issue %s: %s", issue_id, err)
            return None

        return IssueContent(
            title=issue.title or "",
            description=issue.body or "",
        )

    def publish_guide(self, pr_url: PRUrl, guide: ReviewGuide) -> None:
        pr = _get_pr(self.client, pr_url)
        try:
            commit = pr.base.repo.get_commit(pr.head.sha)
            pr.create_review(
                body=self.formatter.format_guide(guide),
                event="COMMENT",
                comments=[],
                commit=commit,
            )
        except github.GithubException as err:
            raise PublishGuideError from err

    def get_file_contents(self, pr_url: PRUrl, file_path: str, branch_name: ContextBranch) -> str | None:
        repo = _get_repo(self.client, pr_url.repo_path)
        pr = _get_pr(self.client, pr_url)
        try:
            file_contents = repo.get_contents(file_path, ref=pr.head.ref if branch_name == "source" else pr.base.ref)
        except github.GithubException as err:
            logger.error(
                "Failed to retrieve file %s from GitHub branch %s, error: %s",
                file_path,
                branch_name,
                err,
            )
            return None

        decoded_content = []
        if not isinstance(file_contents, list):
            file_contents = [file_contents]
        for file_content in file_contents:
            try:
                decoded_bytes = file_content.decoded_content
                if decoded_bytes is None:
                    logger.warning(
                        "Content for file %s on branch %s is not available directly (e.g., too large, or a directory/submodule), skipping for context.",
                        file_path,
                        branch_name,
                    )
                    return None
                decoded_chunk_content = decoded_bytes.decode("utf-8")
            except (binascii.Error, UnicodeDecodeError):
                logger.error(
                    "Failed to decode file %s from GitHub sha: %s, ignoring...",
                    file_path,
                    branch_name,
                )
                return None
            decoded_content.append(decoded_chunk_content)
        return "".join(decoded_content)


@lru_cache(maxsize=64)
def _get_repo(client: github.Github, repo_path: str) -> github.Repository.Repository:
    """Return the repository object for the given pull request URL."""
    try:
        repo = client.get_repo(repo_path)
    except github.GithubException as err:
        logger.error("Failed to retrieve the repository")
        raise PullRequestDiffError from err
    return repo


@lru_cache(maxsize=64)
def _get_pr(client: github.Github, pr_url: PRUrl) -> github.PullRequest.PullRequest:
    """Return the pull request object for the given pull request URL."""
    try:
        repo = _get_repo(client, pr_url.repo_path)
        pr = repo.get_pull(pr_url.pr_number)
    except github.GithubException as err:
        logger.error("Failed to retrieve the pull request")
        raise PullRequestDiffError from err
    return pr


def _get_repo_from_issues_url(client: github.Github, issues_url: HttpUrl) -> github.Repository.Repository:
    """Get the project from the GitHub client using the project path from the issues URL."""
    parsed = urlparse(str(issues_url))
    parts = parsed.path.strip("/").split("/")
    if len(parts) < 3:
        raise ValueError("Invalid GitHub issues URL")
    repo_path = f"{parts[0]}/{parts[1]}"
    return _get_repo(client, repo_path)

import binascii
import logging
from functools import lru_cache

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
from lgtm_ai.git_client.schemas import ContextBranch, PRContext, PRContextFileContents, PRDiff, PRMetadata
from lgtm_ai.git_parser.parser import DiffFileMetadata, DiffResult, parse_diff_patch

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
            parsed_diff = parse_diff_patch(metadata=metadata, diff_text=file.patch)
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
        logger.info("Review published successfully")

    def get_context(self, pr_url: PRUrl, pr_diff: PRDiff) -> PRContext:
        """Return a PRContext object containing the context of the given pull request URL."""
        try:
            pr = _get_pr(self.client, pr_url)
            files = pr.get_files()
        except github.GithubException:
            logger.error("Failed to retrieve the context of the pull request, skipping...")
            return PRContext(file_contents=[])

        context_files: list[PRContextFileContents] = []
        for file in files:
            # Attempt to download the file context from the PR branch
            context_content = self._get_context_file_contents(pr_url=pr_url, file=file, branch_name="source")
            if context_content is None:
                logger.warning(
                    "File %s is not available in the source branch %s, trying target branch...",
                    file.filename,
                    pr_diff.source_branch,
                )
                # If the file is not available in the source branch, try the target branch
                context_content = self._get_context_file_contents(pr_url=pr_url, file=file, branch_name="target")

                if context_content is None:
                    logger.warning(
                        "File %s is not available in the target branch %s, skipping...",
                        file.filename,
                        pr_diff.target_branch,
                    )
                    continue
            context_files.append(context_content)
        return PRContext(file_contents=context_files)

    def get_pr_metadata(self, pr_url: PRUrl) -> PRMetadata:
        """Return a PRMetadata object containing the metadata of the given pull request URL."""
        try:
            pr = _get_pr(self.client, pr_url)
        except github.GithubException as err:
            logger.error("Failed to retrieve the metadata of the pull request")
            raise PullRequestMetadataError from err

        return PRMetadata(title=pr.title or "", description=pr.body or "")

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
        repo = _get_repo(self.client, pr_url)
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

    def _get_context_file_contents(
        self,
        pr_url: PRUrl,
        file: github.File.File,
        branch_name: ContextBranch,
    ) -> PRContextFileContents | None:
        """Return the contents of the given file from the given repository and branch."""
        file_contents = self.get_file_contents(
            file_path=file.filename,
            pr_url=pr_url,
            branch_name=branch_name,
        )
        if file_contents is None:
            return None

        return PRContextFileContents(
            file_path=file.filename,
            content=file_contents,
            branch=branch_name,
        )


@lru_cache(maxsize=64)
def _get_repo(client: github.Github, pr_url: PRUrl) -> github.Repository.Repository:
    """Return the repository object for the given pull request URL."""
    try:
        repo = client.get_repo(pr_url.repo_path)
    except github.GithubException as err:
        logger.error("Failed to retrieve the repository")
        raise PullRequestDiffError from err
    return repo


@lru_cache(maxsize=64)
def _get_pr(client: github.Github, pr_url: PRUrl) -> github.PullRequest.PullRequest:
    """Return the pull request object for the given pull request URL."""
    try:
        repo = _get_repo(client, pr_url)
        pr = repo.get_pull(pr_url.pr_number)
    except github.GithubException as err:
        logger.error("Failed to retrieve the pull request")
        raise PullRequestDiffError from err
    return pr

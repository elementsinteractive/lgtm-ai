import base64
import binascii
import functools
import logging
from typing import Any, cast

import gitlab
import gitlab.exceptions
import gitlab.v4
import gitlab.v4.objects
from lgtm_ai.ai.schemas import Review, ReviewComment, ReviewGuide
from lgtm_ai.base.schemas import PRUrl
from lgtm_ai.formatters.base import Formatter
from lgtm_ai.git_client.base import GitClient
from lgtm_ai.git_client.exceptions import (
    InvalidGitAuthError,
    PublishGuideError,
    PublishReviewError,
    PullRequestDiffError,
    PullRequestDiffNotFoundError,
)
from lgtm_ai.git_client.schemas import ContextBranch, PRContext, PRDiff, PRMetadata
from lgtm_ai.git_parser.exceptions import GitDiffParseError
from lgtm_ai.git_parser.parser import DiffFileMetadata, DiffResult, parse_diff_patch

logger = logging.getLogger("lgtm.git")


class GitlabClient(GitClient):
    def __init__(self, client: gitlab.Gitlab, formatter: Formatter[str]) -> None:
        self.client = client
        self.formatter = formatter
        self._pr: gitlab.v4.objects.ProjectMergeRequest | None = None

    def get_diff_from_url(self, pr_url: PRUrl) -> PRDiff:
        """Return a PRDiff object containing an identifier to the diff and a stringified representation of the diff from latest version of the given pull request URL."""
        try:
            self.client.auth()
            logger.info("Authenticated with GitLab")
        except gitlab.exceptions.GitlabAuthenticationError as err:
            logger.error("Invalid GitLab authentication token")
            raise InvalidGitAuthError from err

        logger.info("Fetching diff from GitLab")
        try:
            pr = _get_pr_from_url(self.client, pr_url)
            diff = self._get_diff_from_pr(pr)
        except gitlab.exceptions.GitlabError as err:
            logger.error("Failed to retrieve the diff of the pull request")
            raise PullRequestDiffError from err

        return PRDiff(
            id=diff.id,
            diff=self._parse_gitlab_git_diff(diff.diffs),
            changed_files=[change["new_path"] for change in diff.diffs],
            target_branch=pr.target_branch,
            source_branch=pr.source_branch,
        )

    def get_context(self, pr_url: PRUrl, pr_diff: PRDiff) -> PRContext:
        """Get the context by using the GitLab API to retrieve the files in the PR diff.

        It mimics the information a human reviewer might have access to, which usually implies
        only looking at the PR in question.
        """
        logger.info("Fetching context from GitLab")
        context = PRContext(file_contents=[])
        branch: ContextBranch = "source"
        for file_path in pr_diff.changed_files:
            branch = "source"
            content = self.get_file_contents(file_path=file_path, pr_url=pr_url, branch_name=branch)
            if content is None:
                logger.warning(
                    "Failed to retrieve file %s from source branch, attempting to retrieve from target branch...",
                    file_path,
                )
                branch = "target"
                content = self.get_file_contents(file_path=file_path, pr_url=pr_url, branch_name="target")
                if content is None:
                    logger.warning("Failed to retrieve file %s from target branch, skipping...", file_path)
                    continue
            context.add_file(file_path, content, branch)
        return context

    def get_pr_metadata(self, pr_url: PRUrl) -> PRMetadata:
        pr = _get_pr_from_url(self.client, pr_url)
        return PRMetadata(
            title=pr.title or "",
            description=pr.description or "",
        )

    def publish_review(self, pr_url: PRUrl, review: Review) -> None:
        logger.info("Publishing review to GitLab")
        try:
            pr = _get_pr_from_url(self.client, pr_url)
            failed_comments = self._post_review_comments(pr, review)
            self._post_review_summary(pr, review, failed_comments)
        except gitlab.exceptions.GitlabError as err:
            raise PublishReviewError from err

    def publish_guide(self, pr_url: PRUrl, guide: ReviewGuide) -> None:
        try:
            pr = _get_pr_from_url(self.client, pr_url)
            pr.notes.create({"body": self.formatter.format_guide(guide)})
        except gitlab.exceptions.GitlabError as err:
            raise PublishGuideError from err

    def get_file_contents(self, pr_url: PRUrl, file_path: str, branch_name: ContextBranch) -> str | None:
        project = _get_project_from_url(self.client, pr_url)
        pr = _get_pr_from_url(self.client, pr_url)
        try:
            file = project.files.get(
                file_path=file_path,
                ref=pr.sha if branch_name == "source" else pr.target_branch,
            )
        except gitlab.exceptions.GitlabError:
            logger.warning("Failed to retrieve file %s from GitLab sha: %s.", file_path, pr.sha)
            return None

        try:
            content = base64.b64decode(file.content).decode()
        except (binascii.Error, UnicodeDecodeError):
            logger.warning("Failed to decode file %s from GitLab sha: %s, ignoring...", file_path, pr.sha)
            return None
        return content

    def _parse_gitlab_git_diff(self, diffs: list[dict[str, object]]) -> list[DiffResult]:
        parsed_diffs: list[DiffResult] = []
        for diff in diffs:
            try:
                diff_text = diff.get("diff")
                if diff_text is None:
                    logger.warning("Diff text is empty, skipping..., diff: %s", diff)
                    continue
                parsed = parse_diff_patch(
                    metadata=DiffFileMetadata.model_validate(diff),
                    diff_text=cast(str, diff_text),
                )
            except GitDiffParseError:
                logger.exception("Failed to parse diff patch, will skip it")
                continue
            parsed_diffs.append(parsed)

        return parsed_diffs

    def _post_review_summary(
        self, pr: gitlab.v4.objects.ProjectMergeRequest, review: Review, failed_comments: list[ReviewComment]
    ) -> None:
        pr.notes.create({"body": self.formatter.format_review_summary_section(review, failed_comments)})

    def _post_review_comments(self, pr: gitlab.v4.objects.ProjectMergeRequest, review: Review) -> list[ReviewComment]:
        """Post comments on the file & filenumber they refer to.

        The AI currently makes mistakes which make gitlab fail to accurately post a comment.
        For example with the line number a comment refers to (whether it's a line on the 'old' file vs the 'new file).
        To avoid blocking the review, we try once with `new_line`, retry with `old_line`, then try to post the comment on the file level and finally return the comments to be posted with the main summary.
        TODO: Rework the prompt & the ReviewResponse so that the AI can be more accurate in providing the line & file information

        Returns:
            list[ReviewComment]: list of comments that could not be created, and therefore should be appended to the review summary
        """
        logger.info("Posting comments to GitLab")
        failed_comments: list[ReviewComment] = []

        diff = pr.diffs.get(review.pr_diff.id)
        for review_comment in review.review_response.comments:
            position = {
                "base_sha": diff.base_commit_sha,
                "head_sha": diff.head_commit_sha,
                "start_sha": diff.start_commit_sha,
                "new_path": review_comment.new_path,
                "old_path": review_comment.old_path,
                "position_type": "text",
            }
            if review_comment.is_comment_on_new_path:
                position["new_line"] = review_comment.line_number
            else:
                position["old_line"] = review_comment.line_number

            gitlab_comment = {
                "body": self.formatter.format_review_comment(review_comment),
                "position": position,
            }

            comment_create_success = self._attempt_comment_at_positions(pr, gitlab_comment)

            if not comment_create_success:
                # Add it to the list of failed comments to be published in the summary comment
                failed_comments.append(review_comment)

        if failed_comments:
            logger.warning(
                "Some comments could not be posted to GitLab; total: %d, failed: %d",
                len(review.review_response.comments),
                len(failed_comments),
            )
        return failed_comments

    def _attempt_comment_at_positions(
        self, pr: gitlab.v4.objects.ProjectMergeRequest, gitlab_comment: dict[str, Any]
    ) -> bool:
        """Try to post comments at decreasingly specific positions.

        By default we want to just try original target, then swap lines, then post to file, then give up.

        Returns whether any of the attempts were successful.
        """
        comment_create_success: bool = True
        try:
            pr.discussions.create(gitlab_comment)
        except gitlab.exceptions.GitlabError:
            comment_create_success = False

        position = gitlab_comment["position"]
        if not comment_create_success:
            # Switch new_line <-> old_line in case the AI made a mistake with `is_comment_on_new_path`
            logger.debug("Failed to post comment, retrying with new_line <-> old_line")
            if "old_line" in position:
                position["new_line"] = position.pop("old_line")
            else:
                position["old_line"] = position.pop("new_line")

            comment_create_success = True
            try:
                pr.discussions.create(gitlab_comment)
            except gitlab.exceptions.GitlabError:
                comment_create_success = False

        if not comment_create_success:
            # Failed to attach to a line, so let's try at file level
            logger.debug("Failed to post for neither line, retrying with a file-level comment")
            _ = position.pop("new_line", None)
            _ = position.pop("old_line", None)
            position["position_type"] = "file"

            comment_create_success = True
            try:
                pr.discussions.create(gitlab_comment)
            except gitlab.exceptions.GitlabError:
                comment_create_success = False
                logger.debug(
                    "Failed to post the comment anywhere specific, it will go to general decription (hopefully)"
                )

        return comment_create_success

    def _get_diff_from_pr(self, pr: gitlab.v4.objects.ProjectMergeRequest) -> gitlab.v4.objects.ProjectMergeRequestDiff:
        """Gitlab returns multiple "diff" objects for a single MR, which correspond to each pushed "version" of the MR.

        We only need to review the latest one, which is the first in the list.
        """
        try:
            latest_diff = next(iter(pr.diffs.list()))
        except StopIteration as err:
            raise PullRequestDiffNotFoundError from err

        return pr.diffs.get(latest_diff.id)


@functools.lru_cache(maxsize=32)
def _get_pr_from_url(client: gitlab.Gitlab, pr_url: PRUrl) -> gitlab.v4.objects.ProjectMergeRequest:
    logger.debug("Fetching mr from GitLab (cache miss)")
    project = _get_project_from_url(client, pr_url)
    return project.mergerequests.get(pr_url.pr_number)


@functools.lru_cache(maxsize=32)
def _get_project_from_url(client: gitlab.Gitlab, pr_url: PRUrl) -> gitlab.v4.objects.Project:
    """Get the project from the GitLab client using the project path from the PR URL."""
    logger.debug("Fetching project from GitLab (cache miss)")
    return client.projects.get(pr_url.repo_path)

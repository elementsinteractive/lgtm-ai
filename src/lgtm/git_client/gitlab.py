import functools
import json

import gitlab
import gitlab.exceptions
import gitlab.v4
import gitlab.v4.objects
from lgtm.ai.schemas import Review, ReviewComment
from lgtm.git_client.base import GitClient
from lgtm.git_client.exceptions import (
    InvalidGitAuthError,
    PublishReviewError,
    PullRequestDiffError,
    PullRequestDiffNotFoundError,
)
from lgtm.git_client.schemas import PRDiff
from lgtm.schemas import GitlabPRUrl


class GitlabClient(GitClient[GitlabPRUrl]):
    def __init__(self, client: gitlab.Gitlab) -> None:
        self.client = client
        self._pr: gitlab.v4.objects.ProjectMergeRequest | None = None

    def get_diff_from_url(self, pr_url: GitlabPRUrl) -> PRDiff:
        """Return a PRDiff object containing an identifier to the diff and a stringified representation of the diff from latest version of the given pull request URL."""
        try:
            self.client.auth()
        except gitlab.exceptions.GitlabAuthenticationError as err:
            raise InvalidGitAuthError from err

        try:
            pr = _get_pr_from_url(self.client, pr_url)
            diff = self._get_diff_from_pr(pr)
        except gitlab.exceptions.GitlabError as err:
            raise PullRequestDiffError from err

        return PRDiff(diff.id, json.dumps(diff.diffs))

    def post_review(self, pr_url: GitlabPRUrl, review: Review) -> None:
        try:
            pr = _get_pr_from_url(self.client, pr_url)
            failed_comments = self._post_comments(pr, review)
            self._post_summary(pr, review, failed_comments)
        except gitlab.exceptions.GitlabError as err:
            raise PublishReviewError from err

    def _post_summary(
        self, pr: gitlab.v4.objects.ProjectMergeRequest, review: Review, failed_comments: list[ReviewComment]
    ) -> None:
        pr.notes.create({"body": self._get_summary_body(review, failed_comments)})

    def _post_comments(self, pr: gitlab.v4.objects.ProjectMergeRequest, review: Review) -> list[ReviewComment]:
        """Post comments on the file & filenumber they refer to.

        The AI currently makes mistakes which make gitlab fail to accurately post a comment.
        For example with the line number a comment refers to (whether it's a line on the 'old' file vs the 'new file).
        To avoid blocking the review, we try once with `new_line`, retry with `old_line` and otherwise return the comments to be posted with the main summary.
        TODO: Rework the prompt & the ReviewResponse so that the AI can be more accurate in providing the line & file information

        Returns:
            list[ReviewComment]: list of comments that could not be created, and therefore should be appended to the review summary
        """
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
                "body": f"🦉 {review_comment.comment}",
                "position": position,
            }

            try:
                pr.discussions.create(gitlab_comment)
            except gitlab.exceptions.GitlabError:
                # Switch new_line <-> old_line in case the AI made a mistake with `is_comment_on_new_path`
                if "old_line" in position:
                    position["new_line"] = position.pop("old_line")
                else:
                    position["old_line"] = position.pop("new_line")
                gitlab_comment["position"] = position

                try:
                    pr.discussions.create(gitlab_comment)
                except gitlab.exceptions.GitlabError:
                    # Add it to the list of failed comments to be published in the summary comment
                    failed_comments.append(review_comment)

        return failed_comments

    def _get_summary_body(self, review: Review, failed_comments: list[ReviewComment]) -> str:
        """Generate a comment body for the given review.

        Note that it is a single comment with a summary and a list of specific comments.
        This should be changed to inline comments in the PR (see #5)
        """
        lines = [
            "🦉 **lgtm Review**",
            f"**Summary:**\n\n>{review.review_response.summary}",
        ]
        if failed_comments:
            lines.extend(
                [
                    "**Specific Comments:**",
                    "\n\n".join(
                        [
                            f"- [ ] _{comment.new_path}:{comment.line_number}_ {comment.comment}"
                            for comment in failed_comments
                        ]
                    ),
                ]
            )
        return "\n\n".join(lines)

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
def _get_pr_from_url(client: gitlab.Gitlab, pr_url: GitlabPRUrl) -> gitlab.v4.objects.ProjectMergeRequest:
    project = client.projects.get(pr_url.project_path)
    return project.mergerequests.get(pr_url.mr_number)

import functools
import json

import gitlab
import gitlab.exceptions
import gitlab.v4
import gitlab.v4.objects
from lgtm.ai.schemas import ReviewResponse
from lgtm.git_client.base import GitClient
from lgtm.git_client.exceptions import (
    InvalidGitAuthError,
    PublishReviewError,
    PullRequestDiffError,
)
from lgtm.schemas import GitlabPRUrl


class GitlabClient(GitClient[GitlabPRUrl]):
    def __init__(self, client: gitlab.Gitlab) -> None:
        self.client = client
        self._pr: gitlab.v4.objects.ProjectMergeRequest | None = None

    def get_diff_from_url(self, pr_url: GitlabPRUrl) -> str:
        """Return a stringified representation of the diffs from the given pull request URL.

        TODO: For GitLab, we are returning a json with the direct response from the API.
        We may decide to refine this later on.
        """
        try:
            self.client.auth()
        except gitlab.exceptions.GitlabAuthenticationError as err:
            raise InvalidGitAuthError from err

        try:
            pr = _get_pr_from_url(self.client, pr_url)
            diffs = self._collect_diffs_from_pr(pr)
        except gitlab.exceptions.GitlabError as err:
            raise PullRequestDiffError from err

        return json.dumps(diffs)

    def post_review(self, pr_url: GitlabPRUrl, review: ReviewResponse) -> None:
        try:
            pr = _get_pr_from_url(self.client, pr_url)
            pr.notes.create({"body": self._get_comment_body(review)})
        except gitlab.exceptions.GitlabError as err:
            raise PublishReviewError from err

    def _get_comment_body(self, review: ReviewResponse) -> str:
        """Generate a comment body for the given review.

        Note that it is a single comment with a summary and a list of specific comments.
        This should be changed to inline comments in the PR (see #5)
        """
        lines = [
            "🦉 **lgtm Review**",
            f"**Summary:**\n\n>{review.summary}",
            "**Specific Comments:**",
        ]
        lines.append(
            "\n\n".join(
                [f"- [ ] _{comment.file}:{comment.line_number}_ {comment.comment}" for comment in review.comments]
            )
        )
        return "\n\n".join(lines)

    def _collect_diffs_from_pr(self, pr: gitlab.v4.objects.ProjectMergeRequest) -> list[object]:
        """Gitlab returns multiple "diff" objects for a single MR. We need to collect them all and concatenate them."""
        diffs = pr.diffs.list()
        full_diffs = []
        for diff in diffs:
            full_diff = pr.diffs.get(diff.id)
            full_diffs.append(full_diff.diffs)
        return full_diffs


@functools.lru_cache(maxsize=32)
def _get_pr_from_url(client: gitlab.Gitlab, pr_url: GitlabPRUrl) -> gitlab.v4.objects.ProjectMergeRequest:
    project = client.projects.get(pr_url.project_path)
    return project.mergerequests.get(pr_url.mr_number)

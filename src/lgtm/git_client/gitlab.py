import json

import gitlab
import gitlab.exceptions
import gitlab.v4
import gitlab.v4.objects
from lgtm.git_client.base import GitClient
from lgtm.git_client.exceptions import (
    InvalidGitAuthError,
    PullRequestDiffError,
)
from lgtm.schemas import GitlabPRUrl


class GitlabClient(GitClient[GitlabPRUrl]):
    def __init__(self, client: gitlab.Gitlab) -> None:
        self.client = client

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
            project = self.client.projects.get(pr_url.project_path)
            pr = project.mergerequests.get(pr_url.mr_number)
            diffs = self._collect_diffs_from_pr(pr)
        except gitlab.exceptions.GitlabError as err:
            raise PullRequestDiffError from err

        return json.dumps(diffs)

    def _collect_diffs_from_pr(self, pr: gitlab.v4.objects.ProjectMergeRequest) -> list[object]:
        """Gitlab returns multiple "diff" objects for a single MR. We need to collect them all and concatenate them."""
        diffs = pr.diffs.list()
        full_diffs = []
        for diff in diffs:
            full_diff = pr.diffs.get(diff.id)
            full_diffs.append(full_diff.diffs)
        return full_diffs

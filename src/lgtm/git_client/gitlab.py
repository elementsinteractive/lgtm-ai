import json
from urllib.parse import urlparse

import gitlab
import gitlab.exceptions
import gitlab.v4
import gitlab.v4.objects
from lgtm.git_client.exceptions import (
    DiffsCollectionError,
    InvalidGitAuthError,
    ProjectNotFoundError,
    PullRequestNotFoundError,
)


class GitlabClient:
    def __init__(self, client: gitlab.Gitlab) -> None:
        self.client = client

    def get_diff_from_url(self, pr_url: str) -> str:
        """Return a stringified representation of the diffs from the given pull request URL.

        TODO: For GitLab, we are returning a json with the direct response from the API.
        We may decide to refine this later on.


        TODO: The error handling and the url parsing is quite cursed.
        """
        try:
            self.client.auth()
        except gitlab.exceptions.GitlabAuthenticationError as err:
            raise InvalidGitAuthError from err

        parsed_url = urlparse(pr_url)
        full_project_path = parsed_url.path
        project_path, mr = full_project_path.split("/-/")

        try:
            project = self.client.projects.get(project_path[1:])
        except gitlab.exceptions.GitlabError as err:
            raise ProjectNotFoundError from err

        try:
            mr_num = int(mr.split("/")[-1])
            pr = project.mergerequests.get(int(mr_num))
        except (gitlab.exceptions.GitlabError, TypeError, ValueError, IndexError) as err:
            raise PullRequestNotFoundError from err

        try:
            diffs = self._collect_diffs_from_pr(pr)
        except gitlab.exceptions.GitlabError as err:
            raise DiffsCollectionError from err

        return json.dumps(diffs)

    def _collect_diffs_from_pr(self, pr: gitlab.v4.objects.ProjectMergeRequest) -> list[object]:
        """Gitlab returns multiple "diff" objects for a single MR. We need to collect them all and concatenate them."""
        diffs = pr.diffs.list()
        full_diffs = []
        for diff in diffs:
            full_diff = pr.diffs.get(diff.id)
            full_diffs.append(full_diff.diffs)
        return full_diffs

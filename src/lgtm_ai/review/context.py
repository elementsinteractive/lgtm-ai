import logging
import pathlib
import re
from typing import Protocol
from urllib.parse import ParseResult, urlparse

import httpx
from lgtm_ai.ai.schemas import (
    AdditionalContext,
)
from lgtm_ai.base.exceptions import LGTMException
from lgtm_ai.base.schemas import LocalRepository, PRUrl
from lgtm_ai.git.repository import get_file_contents_from_local_repo
from lgtm_ai.git_client.base import GitClient
from lgtm_ai.git_client.schemas import ContextBranch, IssueContent, PRDiff, PRMetadata
from lgtm_ai.review.schemas import PRCodeContext
from pydantic import HttpUrl

logger = logging.getLogger("lgtm.ai")


class IssuesClient(Protocol):
    def get_issue_content(self, issues_url: HttpUrl, issue_id: str) -> IssueContent | None:
        """Fetch the content of an issue from the base URL of the issues page."""


class ContextRetriever:
    """Retrieves context for a given PR.

    "Context" is defined as "whatever information the LLM might need (apart from the git diff) to make better reviews or guides".
    """

    def __init__(
        self, git_client: GitClient | None, issues_client: IssuesClient | None, httpx_client: httpx.Client
    ) -> None:
        self._git_client = git_client
        self._issues_client = issues_client
        self._httpx_client = httpx_client

    def get_code_context(self, target: PRUrl | LocalRepository, pr_diff: PRDiff) -> PRCodeContext:
        """Get the code context from the repository.

        It mimics the information a human reviewer might have access to, which usually implies
        only looking at the PR in question.
        """
        logger.info("Fetching code context from repository")
        context = PRCodeContext(file_contents=[])
        branch: ContextBranch = "source"
        for file_path in pr_diff.changed_files:
            logger.debug("Fetching content for file %s", file_path)
            if self._git_client and isinstance(target, PRUrl):
                branch = "source"
                content = self._git_client.get_file_contents(file_path=file_path, pr_url=target, branch_name=branch)
                if content is None:
                    logger.warning(
                        "Failed to retrieve file %s from source branch, attempting to retrieve from target branch...",
                        file_path,
                    )
                    branch = "target"
                    content = self._git_client.get_file_contents(
                        file_path=file_path, pr_url=target, branch_name="target"
                    )
                    if content is None:
                        logger.warning("Failed to retrieve file %s from target branch, skipping...", file_path)
                        continue
            elif isinstance(target, LocalRepository):
                content = get_file_contents_from_local_repo(target.repo_path, pathlib.Path(file_path))
                branch = "source"
            else:
                # This should never happen, but it is technically a possible code path.
                # If there is a PRUrl, then the git client will always be set.
                raise LGTMException("Invalid pr_url type or git_client not configured")
            context.add_file(file_path, content, branch)
        return context

    def get_additional_context(
        self, pr_url: PRUrl | LocalRepository, additional_context: tuple[AdditionalContext, ...]
    ) -> list[AdditionalContext] | None:
        """Get additional context content for the AI model to review the PR.

        From the provided additional context configurations it returns a list of `AdditionalContext` that contains
        the necessary additional context contents to generate a prompt for the AI.

        It either downloads the content from the provided URLs directly (no authentication/custom headers supported)
        or retrieves the content from the repository URL if the given context is a relative path. If no file URL
        is provided for a particular context, it will be returned as is, assuming the `context` field contains the necessary content.
        """
        logger.info("Fetching additional context")
        extra_context: list[AdditionalContext] = []
        for context in additional_context:
            if context.file_url:
                parsed_url = urlparse(context.file_url)
                if self._is_relative_path(parsed_url):
                    if isinstance(pr_url, PRUrl):
                        content = self._download_content_from_repository(pr_url, context.file_url)
                    else:
                        content = get_file_contents_from_local_repo(pr_url.repo_path, pathlib.Path(context.file_url))

                    if content:
                        extra_context.append(
                            AdditionalContext(
                                prompt=context.prompt,
                                file_url=context.file_url,
                                context=content,
                            )
                        )
                else:
                    # If the URL is absolute, we just attempt to download it
                    content = self._download_content_from_url(context.file_url)
                    if content:
                        extra_context.append(
                            AdditionalContext(
                                prompt=context.prompt,
                                file_url=context.file_url,
                                context=content,
                            )
                        )
            else:
                # If no file URL is provided, we assume the content is directly in the context config
                extra_context.append(context)

        return extra_context or None

    def get_issues_context(
        self, issues_url: HttpUrl, issues_regex: str, pr_metadata: PRMetadata
    ) -> IssueContent | None:
        """Retrieve the contents of the issue/user story linked to the PR, if any."""
        if not self._issues_client:
            logger.warning("Issues client is not configured, cannot retrieve issue context")
            return None
        issue_code = self._extract_issue_code_from_metadata(pr_metadata, issues_regex)
        if not issue_code:
            logger.info("No issue code found in PR metadata. Skipping issue context retrieval.")
            return None
        logger.info("Found issue code '%s' in PR metadata. Fetching issue content...", issue_code)

        return self._issues_client.get_issue_content(issues_url=issues_url, issue_id=issue_code)

    def _is_relative_path(self, path: ParseResult) -> bool:
        """Check if the path is relative. If it is relative, we assume it is a file in the repository."""
        return not path.netloc and not path.scheme

    def _download_content_from_repository(self, pr_url: PRUrl, file_url: str) -> str | None:
        if not self._git_client:
            raise ValueError("Git client is not configured, cannot download content from repository")
        content = self._git_client.get_file_contents(pr_url=pr_url, file_path=file_url, branch_name="target")
        if not content:
            logger.warning(f"Could not retrieve content for file URL: {file_url}. Skipping this context.")
            return None
        return content

    def _download_content_from_url(self, url: str) -> str | None:
        """Download content from a given URL."""
        try:
            response = self._httpx_client.get(url)
            response.raise_for_status()
        except httpx.RequestError:
            logger.error(f"Failed to download content from URL {url}, skipping.")
            return None
        except httpx.HTTPStatusError as err:
            logger.error(f"HTTP error while downloading content from URL {url}: {err}")
            return None

        return response.text

    def _extract_issue_code_from_metadata(self, pr_metadata: PRMetadata, issues_regex: str) -> str | None:
        pattern = re.compile(issues_regex, re.IGNORECASE)
        for text in (pr_metadata.title, pr_metadata.description):
            matches = []
            for m in pattern.finditer(text):
                first_group = next((g for g in m.groups() if g), None)
                if first_group:
                    matches.append(first_group)
            if matches:
                # TODO: multiple issues?
                issue_id = matches[0]
                if issue_id and issue_id.startswith("#"):
                    issue_id = issue_id[1:]
                return issue_id
        return None

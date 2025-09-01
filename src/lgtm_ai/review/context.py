import logging
from urllib.parse import ParseResult, urlparse

import httpx
from lgtm_ai.ai.schemas import (
    AdditionalContext,
)
from lgtm_ai.base.schemas import PRUrl
from lgtm_ai.git_client.base import GitClient
from lgtm_ai.git_client.schemas import ContextBranch, PRDiff
from lgtm_ai.review.schemas import PRCodeContext

logger = logging.getLogger("lgtm.ai")


class ContextRetriever:
    """Retrieves context for a given PR.

    "Context" is defined as "whatever information the LLM might need (apart from the git diff) to make better reviews or guides".
    """

    def __init__(self, git_client: GitClient, httpx_client: httpx.Client) -> None:
        self._git_client = git_client
        self._httpx_client = httpx_client

    def get_code_context(self, pr_url: PRUrl, pr_diff: PRDiff) -> PRCodeContext:
        """Get the code context from the repository.

        It mimics the information a human reviewer might have access to, which usually implies
        only looking at the PR in question.
        """
        logger.info("Fetching code context from repository")
        context = PRCodeContext(file_contents=[])
        branch: ContextBranch = "source"
        for file_path in pr_diff.changed_files:
            branch = "source"
            content = self._git_client.get_file_contents(file_path=file_path, pr_url=pr_url, branch_name=branch)
            if content is None:
                logger.warning(
                    "Failed to retrieve file %s from source branch, attempting to retrieve from target branch...",
                    file_path,
                )
                branch = "target"
                content = self._git_client.get_file_contents(file_path=file_path, pr_url=pr_url, branch_name="target")
                if content is None:
                    logger.warning("Failed to retrieve file %s from target branch, skipping...", file_path)
                    continue
            context.add_file(file_path, content, branch)
        return context

    def get_additional_context(
        self, pr_url: PRUrl, additional_context: tuple[AdditionalContext, ...]
    ) -> list[AdditionalContext] | None:
        """Get additional context content for the AI model to review the PR.

        From the provided additional context configurations it returns a list of `Additionalcontext` that contains
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
                # Download the file content from the URL
                if self._is_relative_path(parsed_url):
                    content = self._download_content_from_repository(pr_url, context.file_url)
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

    def _is_relative_path(self, path: ParseResult) -> bool:
        """Check if the path is relative. If it is relative, we assume it is a file in the repository."""
        return not path.netloc and not path.scheme

    def _download_content_from_repository(self, pr_url: PRUrl, file_url: str) -> str | None:
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

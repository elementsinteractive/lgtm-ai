import logging
from urllib.parse import ParseResult, urlparse

import httpx
from lgtm_ai.ai.schemas import (
    AdditionalContext,
)
from lgtm_ai.base.schemas import PRUrl
from lgtm_ai.git_client.base import GitClient

logger = logging.getLogger("lgtm.ai")


class AdditionalContextGenerator:
    """Generates additional context for the AI model to review the PR based on the provided configured values."""

    def __init__(self, httpx_client: httpx.Client, git_client: GitClient) -> None:
        self.httpx_client = httpx_client
        self.git_client = git_client

    def get_additional_context_content(
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
        content = self.git_client.get_file_contents(pr_url=pr_url, file_path=file_url, branch_name="target")
        if not content:
            logger.warning(f"Could not retrieve content for file URL: {file_url}. Skipping this context.")
            return None
        return content

    def _download_content_from_url(self, url: str) -> str | None:
        """Download content from a given URL."""
        try:
            response = self.httpx_client.get(url)
            response.raise_for_status()
        except httpx.RequestError:
            logger.error(f"Failed to download content from URL {url}, skipping.")
            return None
        except httpx.HTTPStatusError as err:
            logger.error(f"HTTP error while downloading content from URL {url}: {err}")
            return None

        return response.text

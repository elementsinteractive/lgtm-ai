import logging
from typing import ClassVar

import httpx
from lgtm_ai.git_client.schemas import IssueContent
from pydantic import BaseModel, HttpUrl, ValidationError

logger = logging.getLogger("lgtm")


class JiraIssuesClient:
    API_VERSION: ClassVar[int] = 3

    def __init__(self, issues_user: str, issues_api_key: str, httpx_client: httpx.Client) -> None:
        self._issues_user = issues_user
        self._issues_api_key = issues_api_key
        self._httpx_client = httpx_client

    def get_issue_content(self, issues_url: HttpUrl, issue_id: str) -> IssueContent | None:
        api_url = f"https://{issues_url.host}/rest/api/{self.API_VERSION}/issue/{issue_id}"

        try:
            response = self._httpx_client.get(api_url, auth=(self._issues_user, self._issues_api_key))
            response.raise_for_status()
            jira_issue = _JiraIssueResponse.model_validate(response.json())
            return IssueContent(title=jira_issue.title, description=jira_issue.description_text)
        except httpx.HTTPError:
            logger.error("Error fetching issue content for %s from Jira at %s", issue_id, issues_url.host)
            return None
        except ValidationError as err:
            logger.error("Error parsing issue content for %s from Jira: %s", issue_id, err)
            return None
        except Exception as err:
            logger.error("Unexpected error fetching issue content for %s from Jira: %s", issue_id, err)
            return None


class _JiraDescriptionContent(BaseModel):
    """Represents content within a Jira description paragraph."""

    type: str
    text: str | None = None


class _JiraDescriptionParagraph(BaseModel):
    """Represents a paragraph in Jira description."""

    type: str
    content: list[_JiraDescriptionContent] | None = None


class _JiraDescription(BaseModel):
    """Represents the Jira description document structure."""

    type: str
    version: int
    content: list[_JiraDescriptionParagraph]

    @property
    def plain_text(self) -> str:
        """Convert the description to plain text."""
        text_parts = []
        for paragraph in self.content:
            if paragraph.content:
                paragraph_text = []
                for content_item in paragraph.content:
                    if content_item.text:
                        paragraph_text.append(content_item.text)
                if paragraph_text:
                    text_parts.append("".join(paragraph_text))
        return "\n\n".join(text_parts)


class _JiraIssueFields(BaseModel):
    """Represents the fields section of a Jira issue."""

    summary: str
    description: _JiraDescription | None = None


class _JiraIssueResponse(BaseModel):
    """Represents a complete Jira issue response."""

    id: str
    key: str
    fields: _JiraIssueFields

    @property
    def title(self) -> str:
        """Get the issue title (summary)."""
        return self.fields.summary

    @property
    def description_text(self) -> str:
        """Get the description as plain text."""
        if self.fields.description:
            return self.fields.description.plain_text
        return ""

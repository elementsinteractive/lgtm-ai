"""Tests for Jira issue parsing models."""

from unittest import mock

import httpx
import pytest
from lgtm_ai.git_client.schemas import IssueContent
from lgtm_ai.jira.jira import (
    JiraIssuesClient,
    _JiraIssueResponse,
)
from pydantic import HttpUrl


class TestJiraIssueResponse:
    """Test cases for _JiraIssueResponse model."""

    def test_complete_issue_response(self) -> None:
        """Test parsing complete Jira issue response."""
        data = {
            "id": "138603",
            "key": "PROJ-53",
            "fields": {
                "summary": "Ensure review does not contain comments on non-changed lines",
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "It is generally annoying, and bad practice, to provide feedback of what a PR has not changed.",
                                }
                            ],
                        }
                    ],
                },
            },
        }
        issue = _JiraIssueResponse.model_validate(data)

        assert issue.id == "138603"
        assert issue.key == "PROJ-53"
        assert issue.title == "Ensure review does not contain comments on non-changed lines"
        assert "It is generally annoying" in issue.description_text

    def test_issue_without_description(self) -> None:
        """Test parsing issue without description."""
        data = {"id": "12345", "key": "TEST-1", "fields": {"summary": "Test issue without description"}}
        issue = _JiraIssueResponse.model_validate(data)

        assert issue.id == "12345"
        assert issue.key == "TEST-1"
        assert issue.title == "Test issue without description"
        assert issue.description_text == ""

    def test_real_jira_response(self) -> None:
        """Test parsing with real Jira API response data."""
        data = {
            "id": "328613",
            "key": "PROJ-53",
            "fields": {
                "summary": "Ensure review does not contain comments on non-changed lines",
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "It is generally annoying, and bad practice, to provide feedback of what a PR has not changed.",
                                }
                            ],
                        },
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "It can be good within a human dev team, where it is understood that those problems are general, and issues can be created from them and whatnot. But for an AI reviewer, it can be annoying. Our gitlab client also fails to create comments for them.",
                                }
                            ],
                        },
                        {"type": "paragraph"},
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Make it so that this never happens. Maybe a combination of a prompt change in both reviewer and summarizer agents? Up to you",
                                }
                            ],
                        },
                    ],
                },
            },
        }

        issue = _JiraIssueResponse.model_validate(data)

        assert issue.key == "PROJ-53"
        assert issue.title == "Ensure review does not contain comments on non-changed lines"

        description_text = issue.description_text
        assert "It is generally annoying" in description_text
        assert "It can be good within a human dev team" in description_text
        assert "Make it so that this never happens" in description_text

        # Should have proper paragraph separation
        paragraphs = description_text.split("\n\n")
        assert len(paragraphs) == 3


class TestJiraIssuesClient:
    """Test cases for JiraIssuesClient."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_client = mock.Mock(spec=httpx.Client)
        self.jira_client = JiraIssuesClient(
            issues_user="test@example.com", issues_api_key="test-api-key", httpx_client=self.mock_client
        )

    def test_successful_issue_fetch(self) -> None:
        """Test successful issue content retrieval."""
        # Mock successful HTTP response
        mock_response = mock.Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "id": "12345",
            "key": "TEST-1",
            "fields": {
                "summary": "Test issue",
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Test description"}]}],
                },
            },
        }
        self.mock_client.get.return_value = mock_response

        issues_url = HttpUrl("https://test.atlassian.net")
        result = self.jira_client.get_issue_content(issues_url, "TEST-1")

        assert result is not None
        assert isinstance(result, IssueContent)
        assert result.title == "Test issue"
        assert result.description == "Test description"

        # Verify the API call
        self.mock_client.get.assert_called_once_with(
            "https://test.atlassian.net/rest/api/3/issue/TEST-1", auth=("test@example.com", "test-api-key")
        )

    def test_http_error_handling(self) -> None:
        """Test handling of HTTP errors."""
        self.mock_client.get.side_effect = httpx.HTTPError("Request failed")

        issues_url = HttpUrl("https://test.atlassian.net")
        result = self.jira_client.get_issue_content(issues_url, "TEST-1")

        assert result is None

    def test_validation_error_handling(self) -> None:
        """Test handling of validation errors."""
        # Mock response with invalid data
        mock_response = mock.Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"invalid": "data"}
        self.mock_client.get.return_value = mock_response

        issues_url = HttpUrl("https://test.atlassian.net")
        result = self.jira_client.get_issue_content(issues_url, "TEST-1")

        assert result is None

    @pytest.mark.parametrize(
        ("input_url", "expected_api_url"),
        [
            (
                "https://company.atlassian.net",
                "https://company.atlassian.net/rest/api/3/issue/TEST-1",
            ),
            (
                "https://mycompany.atlassian.net/secure/Dashboard.jspa",
                "https://mycompany.atlassian.net/rest/api/3/issue/TEST-1",
            ),
        ],
    )
    def test_url_parsing(self, input_url: str, expected_api_url: str) -> None:
        """Test URL parsing for different Jira domains."""
        mock_response = mock.Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"id": "12345", "key": "TEST-1", "fields": {"summary": "Test issue"}}
        self.mock_client.get.return_value = mock_response

        issues_url = HttpUrl(input_url)
        result = self.jira_client.get_issue_content(issues_url, "TEST-1")

        # Should return valid IssueContent
        assert result is not None
        assert result.title == "Test issue"

        # Check the API call was made correctly
        self.mock_client.get.assert_called_once_with(expected_api_url, auth=("test@example.com", "test-api-key"))

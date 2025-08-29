from unittest import mock

from lgtm_ai.ai.agent import (
    get_guide_agent_with_settings,
)
from lgtm_ai.ai.schemas import (
    GuideChecklistItem,
    GuideKeyChange,
    GuideReference,
    GuideResponse,
    PublishMetadata,
    ReviewGuide,
)
from lgtm_ai.base.schemas import PRSource, PRUrl
from lgtm_ai.config.handler import ResolvedConfig
from lgtm_ai.git_client.schemas import PRDiff
from lgtm_ai.review.guide import ReviewGuideGenerator
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.test import TestModel
from tests.review.utils import MOCK_DIFF, MockGitClient


def test_get_guide_from_url_valid() -> None:
    test_agent = get_guide_agent_with_settings()
    with test_agent.override(
        model=TestModel(),
    ):
        guide_generator = ReviewGuideGenerator(
            guide_agent=test_agent,
            model=mock.Mock(spec=OpenAIChatModel, model_name="gemini-2.0-flash"),
            git_client=MockGitClient(),
            config=ResolvedConfig(),
        )
        guide = guide_generator.generate_review_guide(
            pr_url=PRUrl(full_url="foo", repo_path="foo", pr_number=1, source=PRSource.gitlab)
        )

    assert guide == ReviewGuide(
        pr_diff=PRDiff(
            id=1,
            diff=MOCK_DIFF,
            changed_files=["file1", "file2"],
            target_branch="main",
            source_branch="feature",
        ),
        guide_response=GuideResponse(
            summary="a",
            key_changes=[GuideKeyChange(file_name="a", description="a")],
            checklist=[GuideChecklistItem(description="a")],
            references=[GuideReference(title="a", url="a")],
        ),
        metadata=PublishMetadata(model_name="gemini-2.0-flash", usages=guide.metadata.usages),
    )

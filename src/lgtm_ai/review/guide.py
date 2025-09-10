import logging

import httpx
from lgtm_ai.ai.schemas import GuideResponse, PublishMetadata, ReviewGuide
from lgtm_ai.base.constants import DEFAULT_HTTPX_TIMEOUT
from lgtm_ai.base.schemas import PRUrl
from lgtm_ai.config.handler import ResolvedConfig
from lgtm_ai.git_client.base import GitClient
from lgtm_ai.review.context import ContextRetriever
from lgtm_ai.review.exceptions import handle_ai_exceptions
from lgtm_ai.review.prompt_generators import PromptGenerator
from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_ai.usage import UsageLimits

logger = logging.getLogger("lgtm.ai")


class ReviewGuideGenerator:
    def __init__(
        self,
        *,
        guide_agent: Agent[None, GuideResponse],
        model: Model,
        git_client: GitClient | None,
        config: ResolvedConfig,
    ) -> None:
        self.guide_agent = guide_agent
        self.model = model
        self.git_client = git_client
        self.config = config
        self.context_retriever = ContextRetriever(
            git_client=git_client, issues_client=git_client, httpx_client=httpx.Client(timeout=DEFAULT_HTTPX_TIMEOUT)
        )

    def generate_review_guide(self, pr_url: PRUrl) -> ReviewGuide:
        if not self.git_client:
            raise ValueError("Git client is not configured, cannot generate review guide")
        pr_diff = self.git_client.get_diff_from_url(pr_url)
        context = self.context_retriever.get_code_context(pr_url, pr_diff)
        metadata = self.git_client.get_pr_metadata(pr_url)
        usage_limits = UsageLimits(input_tokens_limit=self.config.ai_input_tokens_limit)

        prompt_generator = PromptGenerator(self.config, metadata)

        guide_prompt = prompt_generator.generate_guide_prompt(pr_diff=pr_diff, context=context)
        logger.info("Running AI model on the PR diff")
        with handle_ai_exceptions():
            raw_res = self.guide_agent.run_sync(
                model=self.model,
                user_prompt=guide_prompt,
                usage_limits=usage_limits,
            )
        logger.info("Guide generation completed")

        return ReviewGuide(
            pr_diff=pr_diff,
            guide_response=raw_res.output,
            metadata=PublishMetadata(model_name=self.model.model_name, usage=raw_res.usage()),
        )

import logging

import httpx
from lgtm_ai.ai.schemas import (
    PublishMetadata,
    Review,
    ReviewerDeps,
    ReviewResponse,
    SummarizingDeps,
)
from lgtm_ai.base.schemas import PRUrl
from lgtm_ai.config.handler import ResolvedConfig
from lgtm_ai.git_client.base import GitClient
from lgtm_ai.review.additional_context import AdditionalContextGenerator
from lgtm_ai.review.exceptions import (
    handle_ai_exceptions,
)
from lgtm_ai.review.prompt_generators import PromptGenerator
from pydantic_ai import Agent
from pydantic_ai.models import Model

logger = logging.getLogger("lgtm.ai")


class CodeReviewer:
    """Code reviewer that uses pydantic-ai agents to review pull requests."""

    def __init__(
        self,
        *,
        reviewer_agent: Agent[ReviewerDeps, ReviewResponse],
        summarizing_agent: Agent[SummarizingDeps, ReviewResponse],
        model: Model,
        git_client: GitClient,
        config: ResolvedConfig,
    ) -> None:
        self.reviewer_agent = reviewer_agent
        self.summarizing_agent = summarizing_agent
        self.model = model
        self.git_client = git_client
        self.config = config
        self.additional_context_generator = AdditionalContextGenerator(
            httpx_client=httpx.Client(timeout=3), git_client=git_client
        )

    def review_pull_request(self, pr_url: PRUrl) -> Review:
        pr_diff = self.git_client.get_diff_from_url(pr_url)
        context = self.git_client.get_context(pr_url, pr_diff)
        metadata = self.git_client.get_pr_metadata(pr_url)
        additional_context = self.additional_context_generator.get_additional_context_content(
            pr_url=pr_url,
            additional_context=self.config.additional_context,
        )

        prompt_generator = PromptGenerator(self.config, metadata)

        review_prompt = prompt_generator.generate_review_prompt(
            pr_diff=pr_diff, context=context, additional_context=additional_context
        )
        logger.info("Running AI model on the PR diff")
        with handle_ai_exceptions():
            raw_res = self.reviewer_agent.run_sync(
                model=self.model,
                user_prompt=review_prompt,
                deps=ReviewerDeps(
                    configured_technologies=self.config.technologies, configured_categories=self.config.categories
                ),
            )
        logger.info("Initial review completed")
        logger.debug(
            "Initial review score: %d; Number of comments: %d", raw_res.output.raw_score, len(raw_res.output.comments)
        )
        initial_usage = raw_res.usage()
        logger.info(
            f"Initial review usage summary: {initial_usage.requests=} {initial_usage.request_tokens=} {initial_usage.response_tokens=} {initial_usage.total_tokens=}"
        )

        logger.info("Running AI model to summarize the review")
        summary_prompt = prompt_generator.generate_summarizing_prompt(pr_diff=pr_diff, raw_review=raw_res.output)
        with handle_ai_exceptions():
            final_res = self.summarizing_agent.run_sync(
                model=self.model,
                user_prompt=summary_prompt,
                deps=SummarizingDeps(configured_categories=self.config.categories),
            )
        logger.info("Final review completed")
        logger.debug(
            "Final review score: %d; Number of comments: %d", final_res.output.raw_score, len(final_res.output.comments)
        )
        final_usage = final_res.usage()
        logger.info(
            f"Final review usage summary: {final_usage.requests=} {final_usage.request_tokens=} {final_usage.response_tokens=} {final_usage.total_tokens=}"
        )

        return Review(
            pr_diff=pr_diff,
            review_response=final_res.output,
            metadata=PublishMetadata(model_name=self.config.model, usages=[initial_usage, final_usage]),
        )

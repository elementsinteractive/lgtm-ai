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
from lgtm_ai.git_client.schemas import PRDiff
from lgtm_ai.review.context import ContextRetriever
from lgtm_ai.review.exceptions import (
    handle_ai_exceptions,
)
from lgtm_ai.review.prompt_generators import PromptGenerator
from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_ai.usage import RunUsage, UsageLimits

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
        self.context_retriever = ContextRetriever(git_client=git_client, httpx_client=httpx.Client(timeout=3))

    def review_pull_request(self, pr_url: PRUrl) -> Review:
        """Peform a full review of the given pull request URL and return it."""
        total_usage = RunUsage()
        usage_limits = UsageLimits(input_tokens_limit=self.config.ai_input_tokens_limit)
        metadata = self.git_client.get_pr_metadata(pr_url)
        prompt_generator = PromptGenerator(self.config, metadata)
        pr_diff = self.git_client.get_diff_from_url(pr_url)
        initial_review_response = self._perform_initial_review(
            pr_url,
            pr_diff=pr_diff,
            prompt_generator=prompt_generator,
            total_usage=total_usage,
            usage_limits=usage_limits,
        )
        final_review, final_usage = self._summarize_initial_review(
            pr_diff,
            initial_review_response=initial_review_response,
            prompt_generator=prompt_generator,
            total_usage=total_usage,
            usage_limits=usage_limits,
        )
        logger.info("Final review completed")
        logger.debug(
            "Final review score: %d; Number of comments: %d", final_review.raw_score, len(final_review.comments)
        )

        return Review(
            pr_diff=pr_diff,
            review_response=final_review,
            metadata=PublishMetadata(model_name=self.model.model_name, usage=final_usage),
        )

    def _perform_initial_review(
        self,
        pr_url: PRUrl,
        *,
        pr_diff: PRDiff,
        prompt_generator: PromptGenerator,
        total_usage: RunUsage,
        usage_limits: UsageLimits,
    ) -> ReviewResponse:
        """Perform an initial review of the PR with the reviewer agent."""
        context = self.context_retriever.get_code_context(pr_url=pr_url, pr_diff=pr_diff)
        additional_context = self.context_retriever.get_additional_context(
            pr_url=pr_url,
            additional_context=self.config.additional_context,
        )

        review_prompt = prompt_generator.generate_review_prompt(
            pr_diff=pr_diff, context=context, additional_context=additional_context
        )
        logger.info("Running Reviewer agent on the PR diff")
        with handle_ai_exceptions():
            raw_res = self.reviewer_agent.run_sync(
                model=self.model,
                user_prompt=review_prompt,
                deps=ReviewerDeps(
                    configured_technologies=self.config.technologies, configured_categories=self.config.categories
                ),
                usage=total_usage,
                usage_limits=usage_limits,
            )
        logger.info("Initial review completed")
        logger.debug(
            "Initial review score: %d; Number of comments: %d", raw_res.output.raw_score, len(raw_res.output.comments)
        )
        initial_usage = raw_res.usage()
        logger.info(
            f"Initial review usage summary: {initial_usage.requests=} {initial_usage.input_tokens=} {initial_usage.output_tokens=} {initial_usage.total_tokens=}"
        )
        return raw_res.output

    def _summarize_initial_review(
        self,
        pr_diff: PRDiff,
        *,
        initial_review_response: ReviewResponse,
        prompt_generator: PromptGenerator,
        total_usage: RunUsage,
        usage_limits: UsageLimits,
    ) -> tuple[ReviewResponse, RunUsage]:
        """Summarize the initial review with the summarizing agent."""
        logger.info("Running AI model to summarize the review")
        summary_prompt = prompt_generator.generate_summarizing_prompt(
            pr_diff=pr_diff, raw_review=initial_review_response
        )
        with handle_ai_exceptions():
            final_res = self.summarizing_agent.run_sync(
                model=self.model,
                user_prompt=summary_prompt,
                deps=SummarizingDeps(configured_categories=self.config.categories),
                usage=total_usage,
                usage_limits=usage_limits,
            )
        usage = final_res.usage()
        return final_res.output, usage

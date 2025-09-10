import logging

from lgtm_ai.ai.schemas import (
    PublishMetadata,
    Review,
    ReviewerDeps,
    ReviewResponse,
    SummarizingDeps,
)
from lgtm_ai.base.schemas import LocalRepository, PRUrl
from lgtm_ai.config.handler import ResolvedConfig
from lgtm_ai.git.repository import get_diff_from_local_repo
from lgtm_ai.git_client.base import GitClient
from lgtm_ai.git_client.schemas import PRDiff, PRMetadata
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
    """
    CodeReviewer orchestrates the automated review of pull requests using AI agents and contextual information.

    This class coordinates the process of reviewing a pull request (PR) by leveraging two pydantic-ai agents:
    - reviewer_agent: Generates the initial review, including comments and scores, based on the PR diff and context.
    - summarizing_agent: Refines and summarizes the initial review for clarity and conciseness.

    Key responsibilities:
    - Retrieve PR metadata and diffs using a GitClient.
    - Gather code context, additional context, and related issue context for the PR using a ContextRetriever.
    - Generate prompts for the AI agents using a PromptGenerator, tailored to the PR and its context.
    - Run the reviewer agent to produce an initial review, including inline comments and a summary.
    - Optionally fetch and incorporate related issue context if configured.
    - Run the summarizing agent to produce a final, polished review response.
    - Track and aggregate usage statistics for AI model calls.
    - Return a Review object containing the PR diff, final review response, and metadata about the review process.

    Main workflow:
    1. Call review_pull_request(target):
        - Fetch PR metadata and diff.
        - Gather code and additional context, and optionally issue context.
        - Generate a review prompt and run the reviewer agent for the initial review.
        - Summarize the initial review using the summarizing agent.
        - Return a Review object with all results and metadata.

    """

    def __init__(
        self,
        *,
        reviewer_agent: Agent[ReviewerDeps, ReviewResponse],
        summarizing_agent: Agent[SummarizingDeps, ReviewResponse],
        model: Model,
        context_retriever: ContextRetriever,
        git_client: GitClient | None,
        config: ResolvedConfig,
    ) -> None:
        """
        Initialize a CodeReviewer instance.

        Args:
            reviewer_agent (Agent[ReviewerDeps, ReviewResponse]):
                AI agent that generates the initial review, including comments and scores, based on the PR diff and context.
            summarizing_agent (Agent[SummarizingDeps, ReviewResponse]):
                AI agent that refines and summarizes the initial review for clarity and conciseness.
            model (Model):
                The AI model to use for both agents (e.g., GPT-4, Claude, etc.).
            context_retriever (ContextRetriever):
                Utility to gather code context, additional context, and related issue context for the PR.
            git_client (GitClient):
                Abstraction for interacting with the git hosting service (GitHub, GitLab, etc.), used to fetch PR metadata and diffs.
            config (ResolvedConfig):
                The resolved configuration object, containing settings for AI limits, context sources, technologies, categories, and more.
        """
        self.reviewer_agent = reviewer_agent
        self.summarizing_agent = summarizing_agent
        self.model = model
        self.git_client = git_client
        self.config = config
        self.context_retriever = context_retriever

    def review_pull_request(self, target: PRUrl | LocalRepository) -> Review:
        """Peform a full review of the given pull request URL and return it."""
        total_usage = RunUsage()
        usage_limits = UsageLimits(input_tokens_limit=self.config.ai_input_tokens_limit)

        if self.git_client and isinstance(target, PRUrl):
            metadata = self.git_client.get_pr_metadata(target)
            pr_diff = self.git_client.get_diff_from_url(target)
        elif isinstance(target, LocalRepository):
            metadata = PRMetadata(title="Local changes with no PR", description="")
            pr_diff = get_diff_from_local_repo(target.repo_path, compare=self.config.compare)
        else:
            raise ValueError("Invalid pr_url type or git_client not configured")

        prompt_generator = PromptGenerator(self.config, metadata)

        initial_review_response = self._perform_initial_review(
            target,
            pr_diff=pr_diff,
            pr_metadata=metadata,
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
        pr_url: PRUrl | LocalRepository,
        *,
        pr_diff: PRDiff,
        pr_metadata: PRMetadata,
        prompt_generator: PromptGenerator,
        total_usage: RunUsage,
        usage_limits: UsageLimits,
    ) -> ReviewResponse:
        """Perform an initial review of the PR with the reviewer agent."""
        context = self.context_retriever.get_code_context(target=pr_url, pr_diff=pr_diff)
        additional_context = self.context_retriever.get_additional_context(
            pr_url=pr_url,
            additional_context=self.config.additional_context,
        )
        if self.config.issues_platform and self.config.issues_url and self.config.issues_regex:
            logger.info("Fetching issue context related to the PR")
            issue_context = self.context_retriever.get_issues_context(
                issues_url=self.config.issues_url,
                issues_regex=self.config.issues_regex,
                pr_metadata=pr_metadata,
            )
        else:
            issue_context = None

        review_prompt = prompt_generator.generate_review_prompt(
            pr_diff=pr_diff,
            context=context,
            additional_context=additional_context,
            issue_context=issue_context,
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

import json
import logging

from lgtm.ai.schemas import Review, ReviewerDeps, ReviewMetadata, ReviewResponse, SummarizingDeps
from lgtm.base.exceptions import NothingToReviewError
from lgtm.base.schemas import PRUrl
from lgtm.base.utils import file_matches_any_pattern
from lgtm.config.handler import ResolvedConfig
from lgtm.git_client.base import GitClient
from lgtm.git_client.schemas import PRContext, PRContextFileContents, PRDiff, PRMetadata
from pydantic_ai import Agent
from pydantic_ai.models import Model

logger = logging.getLogger("lgtm.ai")


class CodeReviewer:
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

    def review_pull_request(self, pr_url: PRUrl) -> Review:
        pr_diff = self.git_client.get_diff_from_url(pr_url)
        context = self.git_client.get_context(pr_url, pr_diff)
        metadata = self.git_client.get_pr_metadata(pr_url)

        prompt_generator = PromptGenerator(self.config, metadata)

        review_prompt = prompt_generator.generate_review_prompt(pr_diff=pr_diff, context=context)
        logger.info("Running AI model on the PR diff")
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

        logger.info("Running AI model to summarize the review")
        summary_prompt = prompt_generator.generate_summarizing_prompt(pr_diff=pr_diff, raw_review=raw_res.output)
        final_res = self.summarizing_agent.run_sync(
            model=self.model,
            user_prompt=summary_prompt,
            deps=SummarizingDeps(configured_categories=self.config.categories),
        )
        logger.info("Final review completed")
        logger.debug(
            "Final review score: %d; Number of comments: %d", final_res.output.raw_score, len(final_res.output.comments)
        )
        return Review(pr_diff, final_res.output, metadata=ReviewMetadata(model_name=self.config.model))


class PromptGenerator:
    """Generates the prompts for the AI model to review the PR."""

    def __init__(self, config: ResolvedConfig, pr_metadata: PRMetadata) -> None:
        self.config = config
        self.pr_metadata = pr_metadata

    def generate_review_prompt(self, *, pr_diff: PRDiff, context: PRContext) -> str:
        """Generate the initial prompt for the AI model to review the PR.

        It includes the diff and the context of the PR, formatted for the AI to receive.
        """
        # PR metadata section
        pr_metadata_prompt = self._pr_metadata_prompt(self.pr_metadata)
        # Diff section
        diff_prompt = self._pr_diff_prompt(pr_diff)

        # Context section
        context_prompt = ""
        if context:
            all_file_contexts = [
                self._generate_context_prompt_for_file(file_context) for file_context in context.file_contents
            ]
            context_prompt = "Context:\n"
            context_prompt += "\n\n".join(all_file_contexts)

        return (
            f"{pr_metadata_prompt}\n{diff_prompt}\n{context_prompt}"
            if context
            else f"{pr_metadata_prompt}\n{diff_prompt}"
        )

    def generate_summarizing_prompt(self, *, pr_diff: PRDiff, raw_review: ReviewResponse) -> str:
        """Generate a prompt for the AI model to summarize the review.

        It includes the diff and the review, formatted for the AI to receive.
        """
        pr_metadata_prompt = self._pr_metadata_prompt(self.pr_metadata)
        diff_prompt = self._pr_diff_prompt(pr_diff)
        review_prompt = f"Review: {raw_review.model_dump()}\n"
        return f"{pr_metadata_prompt}\n{diff_prompt}\n{review_prompt}"

    def _generate_context_prompt_for_file(self, file_context: PRContextFileContents) -> str:
        """Generate context prompt for a single file in the PR.

        It excludes files according to the `exclude` patterns in the config.
        """
        if file_matches_any_pattern(file_context.file_path, self.config.exclude):
            logger.debug("Excluding file %s from context", file_context.file_path)
            return ""

        content = self._indent(file_context.content)
        return f"    ```{file_context.file_path}\n{content}\n    ```"

    def _pr_diff_prompt(self, pr_diff: PRDiff) -> str:
        return f"PR Diff:\n    ```\n{self._indent(self._serialize_pr_diff(pr_diff))}\n    ```"

    def _pr_metadata_prompt(self, pr_metadata: PRMetadata) -> str:
        return "PR Metadata:\n" + self._indent(
            f"```Title\n{pr_metadata.title}\n```\n" + f"```Description\n{pr_metadata.description or ''}\n```\n"
        )

    def _serialize_pr_diff(self, pr_diff: PRDiff) -> str:
        """Serialize the PR diff to a JSON string for the AI model.

        The PR diff is parsed by the Git client, and contains all the necessary information the AI needs
        to review it. We convert it here to a JSON string so that the AI can process it easily.

        It excludes files according to the `exclude` patterns in the config.
        """
        keep = []
        for diff in pr_diff.diff:
            if not file_matches_any_pattern(diff.metadata.new_path, self.config.exclude):
                keep.append(diff.model_dump())
            else:
                logger.debug("Excluding file %s from diff", diff.metadata.new_path)

        if not keep:
            raise NothingToReviewError(exclude=self.config.exclude)
        return json.dumps(keep)

    def _indent(self, text: str, level: int = 4) -> str:
        """Indent the text by a given number of spaces."""
        indent = " " * level
        return "\n".join(f"{indent}{line}" for line in text.splitlines())

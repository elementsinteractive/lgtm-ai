import logging

from lgtm.ai.schemas import Review, ReviewResponse
from lgtm.base.schemas import PRUrl
from lgtm.git_client.base import GitClient
from lgtm.git_client.schemas import PRContext, PRContextFileContents, PRDiff
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

logger = logging.getLogger("lgtm.ai")


class CodeReviewer:
    def __init__(
        self,
        reviewer_agent: Agent[None, ReviewResponse],
        summarizing_agent: Agent[None, ReviewResponse],
        *,
        model: OpenAIModel,
        git_client: GitClient[PRUrl],
    ) -> None:
        self.reviewer_agent = reviewer_agent
        self.summarizing_agent = summarizing_agent
        self.model = model
        self.git_client = git_client

    def review_pull_request(self, pr_url: PRUrl) -> Review:
        pr_diff = self.git_client.get_diff_from_url(pr_url)
        context = self.git_client.get_context(pr_url, pr_diff)
        review_prompt = self._generate_review_prompt(pr_diff, context)

        logger.info("Running AI model on the PR diff")
        raw_res = self.reviewer_agent.run_sync(model=self.model, user_prompt=review_prompt)
        logger.info("Initial review completed")
        logger.debug(
            "Initial review score: %d; Number of comments: %d", raw_res.data.raw_score, len(raw_res.data.comments)
        )

        logger.info("Running AI model to summarize the review")
        summary_prompt = self._generate_summarizing_prompt(pr_diff, raw_res.data)
        final_res = self.summarizing_agent.run_sync(model=self.model, user_prompt=summary_prompt)
        logger.info("Final review completed")
        logger.debug(
            "Final review score: %d; Number of comments: %d", final_res.data.raw_score, len(final_res.data.comments)
        )
        return Review(pr_diff, final_res.data)

    def _generate_review_prompt(self, pr_diff: PRDiff, context: PRContext) -> str:
        # Diff section
        diff_prompt = f"PR Diff:\n    ```\n{self._indent(pr_diff.diff)}\n    ```"

        # Context section
        context_prompt = ""
        if context:
            all_file_contexts = [
                self._generate_context_prompt_for_file(file_context) for file_context in context.file_contents
            ]
            context_prompt = "Context:\n"
            context_prompt += "\n\n".join(all_file_contexts)

        return f"{diff_prompt}\n{context_prompt}" if context else diff_prompt

    def _generate_summarizing_prompt(self, pr_diff: PRDiff, raw_review: ReviewResponse) -> str:
        diff_prompt = f"PR Diff:\n    ```\n{self._indent(pr_diff.diff)}\n    ```"
        review_prompt = f"Review: {raw_review.model_dump()}\n"
        return f"{diff_prompt}\n{review_prompt}"

    def _generate_context_prompt_for_file(self, file_context: PRContextFileContents) -> str:
        content = self._indent(file_context.content)
        return f"    ```{file_context.file_path}\n{content}\n    ```"

    def _indent(self, text: str, level: int = 4) -> str:
        indent = " " * level
        return "\n".join(f"{indent}{line}" for line in text.splitlines())

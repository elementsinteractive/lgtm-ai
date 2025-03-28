import logging

from lgtm.ai.schemas import Review, ReviewResponse
from lgtm.base.schemas import PRUrl
from lgtm.git_client.base import GitClient
from lgtm.git_client.schemas import PRContext, PRContextFileContents, PRDiff
from pydantic_ai import Agent

logger = logging.getLogger("lgtm.ai")


class CodeReviewer:
    def __init__(self, agent: Agent[None, ReviewResponse], git_client: GitClient[PRUrl]) -> None:
        self.agent = agent
        self.git_client = git_client

    def review_pull_request(self, pr_url: PRUrl) -> Review:
        pr_diff = self.git_client.get_diff_from_url(pr_url)
        context = self.git_client.get_context(pr_url, pr_diff)
        prompt = self._generate_prompt(pr_diff, context)

        logger.info("Running AI model on the PR diff")
        res = self.agent.run_sync(user_prompt=prompt)
        return Review(pr_diff, res.data)

    def _generate_prompt(self, pr_diff: PRDiff, context: PRContext) -> str:
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

    def _generate_context_prompt_for_file(self, file_context: PRContextFileContents) -> str:
        content = self._indent(file_context.content)
        return f"    ```{file_context.file_path}\n{content}\n    ```"

    def _indent(self, text: str, level: int = 4) -> str:
        indent = " " * level
        return "\n".join(f"{indent}{line}" for line in text.splitlines())

import json
import logging

from lgtm_ai.ai.schemas import AdditionalContext, ReviewResponse
from lgtm_ai.base.exceptions import NothingToReviewError
from lgtm_ai.base.utils import file_matches_any_pattern
from lgtm_ai.config.handler import ResolvedConfig
from lgtm_ai.git_client.schemas import PRContext, PRContextFileContents, PRDiff, PRMetadata

logger = logging.getLogger("lgtm.ai")


class PromptGenerator:
    """Generates the prompts for the AI model to review the PR."""

    def __init__(self, config: ResolvedConfig, pr_metadata: PRMetadata) -> None:
        self.config = config
        self.pr_metadata = pr_metadata

    def generate_review_prompt(
        self, *, pr_diff: PRDiff, context: PRContext, additional_context: list[AdditionalContext] | None = None
    ) -> str:
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

        if additional_context:
            all_additional_contexts = [self._generate_additional_context_prompt(ac) for ac in additional_context]
            add_context_prompt = "Additional context:\n"

            if context_prompt:
                context_prompt += f"\n{add_context_prompt}"
            else:
                context_prompt = add_context_prompt

            context_prompt += "\n\n".join(all_additional_contexts)

        return (
            f"{pr_metadata_prompt}\n{diff_prompt}\n{context_prompt}"
            if context or additional_context
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

    def generate_guide_prompt(
        self, *, pr_diff: PRDiff, context: PRContext, additional_context: list[AdditionalContext] | None = None
    ) -> str:
        return self.generate_review_prompt(
            pr_diff=pr_diff, context=context, additional_context=additional_context
        )  # FIXME: They are the same for now?

    def _generate_context_prompt_for_file(self, file_context: PRContextFileContents) -> str:
        """Generate context prompt for a single file in the PR.

        It excludes files according to the `exclude` patterns in the config.
        """
        if file_matches_any_pattern(file_context.file_path, self.config.exclude):
            logger.debug("Excluding file %s from context", file_context.file_path)
            return ""

        content = self._indent(file_context.content)
        return f"    ```{file_context.file_path}, branch={file_context.branch}\n{content}\n    ```"

    def _generate_additional_context_prompt(self, additional_context: AdditionalContext) -> str:
        if not additional_context.context:
            return ""
        context = self._indent(additional_context.context)
        return f"    ```file={additional_context.file_url}; prompt={additional_context.prompt}\n{context}\n    ```"

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

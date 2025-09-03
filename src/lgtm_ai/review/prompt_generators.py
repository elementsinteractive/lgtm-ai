import json
import logging
import pathlib
from typing import ClassVar

from jinja2 import Environment, FileSystemLoader
from lgtm_ai.ai.schemas import AdditionalContext, ReviewResponse
from lgtm_ai.base.exceptions import NothingToReviewError
from lgtm_ai.base.utils import file_matches_any_pattern
from lgtm_ai.config.handler import ResolvedConfig
from lgtm_ai.git_client.schemas import IssueContent, PRDiff, PRMetadata
from lgtm_ai.review.schemas import PRCodeContext, PRContextFileContents

logger = logging.getLogger("lgtm.ai")


class PromptGenerator:
    """Generates the prompts for the AI model to review the PR."""

    REVIEW_TEMPLATE: ClassVar[str] = "review_prompt.txt.j2"
    SUMMARIZING_TEMPLATE: ClassVar[str] = "summarizing_prompt.txt.j2"

    def __init__(self, config: ResolvedConfig, pr_metadata: PRMetadata) -> None:
        self.config = config
        self.pr_metadata = pr_metadata

        template_dir = pathlib.Path(__file__).parent / "templates"
        self._template_env = Environment(loader=FileSystemLoader(template_dir), autoescape=False)  # noqa: S701

    def generate_review_prompt(
        self,
        *,
        pr_diff: PRDiff,
        context: PRCodeContext,
        additional_context: list[AdditionalContext] | None = None,
        issue_context: IssueContent | None = None,
    ) -> str:
        """Generate the initial prompt for the AI model to review the PR.

        It includes the diff and the context of the PR, formatted for the AI to receive.
        """
        template = self._template_env.get_template(self.REVIEW_TEMPLATE)
        return template.render(
            metadata=self.pr_metadata,
            diff=self._serialize_pr_diff(pr_diff),
            context=self._filter_context_based_on_exclusions(context.file_contents),
            issue_context=issue_context,
            additional_context=additional_context,
        )

    def generate_summarizing_prompt(self, *, pr_diff: PRDiff, raw_review: ReviewResponse) -> str:
        """Generate a prompt for the AI model to summarize the review.

        It includes the diff and the review, formatted for the AI to receive.
        """
        template = self._template_env.get_template(self.SUMMARIZING_TEMPLATE)
        return template.render(
            metadata=self.pr_metadata,
            diff=self._serialize_pr_diff(pr_diff),
            review=raw_review.model_dump(),
        )

    def generate_guide_prompt(
        self, *, pr_diff: PRDiff, context: PRCodeContext, additional_context: list[AdditionalContext] | None = None
    ) -> str:
        return self.generate_review_prompt(
            pr_diff=pr_diff, context=context, additional_context=additional_context
        )  # FIXME: They are the same for now?

    def _filter_context_based_on_exclusions(
        self, file_context: list[PRContextFileContents]
    ) -> list[PRContextFileContents]:
        return [fc for fc in file_context if not file_matches_any_pattern(fc.file_path, self.config.exclude)]

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

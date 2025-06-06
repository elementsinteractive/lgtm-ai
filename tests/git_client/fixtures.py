from unittest import mock

from lgtm_ai.ai.schemas import (
    GuideChecklistItem,
    GuideKeyChange,
    GuideReference,
    GuideResponse,
    PublishMetadata,
    ReviewGuide,
)
from lgtm_ai.git_client.schemas import PRDiff
from lgtm_ai.git_parser.parser import DiffFileMetadata, DiffResult, ModifiedLine
from tests.review.utils import MOCK_USAGE

PARSED_GIT_DIFF = [
    DiffResult(
        metadata=DiffFileMetadata(
            new_file=False, deleted_file=False, renamed_file=False, new_path="justfile", old_path="justfile"
        ),
        modified_lines=[
            ModifiedLine(
                line='    {{ run }} ruff check {{ target_dirs }} {{ if report == "true" { "--format gitlab > tests/gl-code-quality-report.json" } else { "" } }}',
                line_number=48,
                relative_line_number=4,
                modification_type="removed",
            ),
            ModifiedLine(
                line='    {{ run }} ruff check {{ target_dirs }} {{ if report == "true" { "--output-format gitlab > tests/gl-code-quality-report.json" } else { "" } }}',
                line_number=48,
                relative_line_number=5,
                modification_type="added",
            ),
        ],
    ),
    DiffResult(
        metadata=DiffFileMetadata(
            new_file=False, deleted_file=False, renamed_file=False, new_path="pyproject.toml", old_path="pyproject.toml"
        ),
        modified_lines=[
            ModifiedLine(
                line="[tool.ruff.per-file-ignores]", line_number=78, relative_line_number=4, modification_type="removed"
            ),
            ModifiedLine(
                line="[tool.ruff.lint.per-file-ignores]",
                line_number=78,
                relative_line_number=5,
                modification_type="added",
            ),
        ],
    ),
]

FAKE_GUIDE = ReviewGuide(
    pr_diff=mock.Mock(spec=PRDiff),
    guide_response=GuideResponse(
        summary="a",
        key_changes=[
            GuideKeyChange(file_name="foo.py", description="description"),
            GuideKeyChange(file_name="bar.py", description="description"),
        ],
        checklist=[GuideChecklistItem(description="item 1")],
        references=[GuideReference(title="title", url="https://example.com")],
    ),
    metadata=PublishMetadata(model_name="whatever", usages=[MOCK_USAGE]),
)

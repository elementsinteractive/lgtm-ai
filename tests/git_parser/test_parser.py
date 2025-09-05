import pytest
from lgtm_ai.git_parser.exceptions import GitDiffParseError
from lgtm_ai.git_parser.parser import DiffResult, parse_diff_patch
from tests.git_parser.fixtures import (
    COMPLEX_DIFF_TEXT,
    DUMMY_METADATA,
    PARSED_REFACTOR_DIFF,
    PARSED_SIMPLE_DIFF,
    REFACTOR_DIFF,
    SIMPLE_DIFF,
)


@pytest.mark.parametrize(
    ("input_diff", "expected"),
    [
        pytest.param(SIMPLE_DIFF, PARSED_SIMPLE_DIFF, id="simple"),
        pytest.param(REFACTOR_DIFF, PARSED_REFACTOR_DIFF, id="refactor"),
    ],
)
def test_parse_diff_patch(input_diff: str, expected: DiffResult) -> None:
    assert parse_diff_patch(DUMMY_METADATA, input_diff) == expected


def test_parse_diff_patch_non_text_files() -> None:
    with pytest.raises(GitDiffParseError, match="Diff text is not a string"):
        parse_diff_patch(DUMMY_METADATA, diff_text=bytes(1234))


@pytest.mark.parametrize(
    ("content", "expected_line"),
    [
        ("from typing import get_args", 4),
        ("printer(formatter.format_review_comments_section(review.review_response.comments))", 75),
        ("assert_never(output_format)", 121),
    ],
)
def test_parse_diff_relative_line_multiple_hunks(content: str, expected_line: int) -> None:
    parsed = parse_diff_patch(DUMMY_METADATA, COMPLEX_DIFF_TEXT)

    parsed_line = next(parsed_line for parsed_line in parsed.modified_lines if content in parsed_line.line)
    assert parsed_line.relative_line_number == expected_line, (
        f"Expected line number {expected_line}, got {parsed_line.line_number}"
    )


def test_parse_diff_hunk_starts_set_correctly() -> None:
    """Test that hunk_start_new and hunk_start_old are correctly set for all modified lines."""
    parsed = parse_diff_patch(DUMMY_METADATA, COMPLEX_DIFF_TEXT)

    # Check that no modified lines have None for hunk starts
    for line in parsed.modified_lines:
        assert line.hunk_start_new is not None, f"hunk_start_new is None for line: {line.line}"
        assert line.hunk_start_old is not None, f"hunk_start_old is None for line: {line.line}"

    # Test specific lines and their expected hunk starts
    expected_hunk_starts = [
        # First hunk @@ -2,7 +2,7 @@
        ("from typing import get_args", 2, 2),
        ("from typing import Any, assert_never, get_args", 2, 2),
        # Second hunk @@ -13,10 +13,12 @@
        ("from lgtm_ai.base.schemas import PRUrl", 13, 13),
        ("from lgtm_ai.base.schemas import OutputFormat, PRUrl", 13, 13),
        ("from lgtm_ai.formatters.base import Formatter", 13, 13),
        # Third hunk @@ -25,14 +27,15 @@
        ("from rich.console import Console", 25, 27),
        # Fourth hunk @@ -68,6 +71,7 @@
        ('@click.option("--output-format", type=click.Choice([format.value for format in OutputFormat]))', 68, 71),
        # Last hunk @@ -220,3 +228,15 @@
        (
            "def _get_formatter_and_printer(output_format: OutputFormat) -> tuple[Formatter[Any], Callable[[Any], None]]:",
            220,
            228,
        ),
    ]

    for content, expected_old, expected_new in expected_hunk_starts:
        matching_lines = [line for line in parsed.modified_lines if content in line.line]
        assert len(matching_lines) > 0, f"No line found containing: {content}"

        line = matching_lines[0]
        assert line.hunk_start_old == expected_old, (
            f"Expected hunk_start_old {expected_old}, got {line.hunk_start_old} for line: {content}"
        )
        assert line.hunk_start_new == expected_new, (
            f"Expected hunk_start_new {expected_new}, got {line.hunk_start_new} for line: {content}"
        )

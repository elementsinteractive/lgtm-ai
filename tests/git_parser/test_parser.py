import pytest
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
        (SIMPLE_DIFF, PARSED_SIMPLE_DIFF),
        (REFACTOR_DIFF, PARSED_REFACTOR_DIFF),
    ],
)
def test_parse_diff_patch(input_diff: str, expected: DiffResult) -> None:
    assert parse_diff_patch(DUMMY_METADATA, input_diff) == expected


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

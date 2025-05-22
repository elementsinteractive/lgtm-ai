import pytest
from lgtm_ai.git_parser.parser import DiffResult, parse_diff_patch
from tests.git_parser.fixtures import (
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

import pytest
from lgtm.base.utils import file_matches_any_pattern


@pytest.mark.parametrize(
    ("file_name", "patterns", "expected_match"),
    [
        ("foo/bar/baz.py", ("*.py",), True),
        ("foo/bar/baz.py", ("foo/*",), True),
        ("foo/bar/baz.py", ("*.txt",), False),
        ("foo/bar/baz.py", ("*.py", "*.txt"), True),
        ("foo/bar/baz.py", ("*.txt", "*.py"), True),
        ("foo/bar/baz.py", ("*.txt", "baz.py"), True),
        ("foo/bar/baz.py", ("baz.py",), True),
        ("foo/bar/baz.py", ("/baz.py",), False),
        ("baz.py", ("/baz.py",), False),
        ("baz.py", ("baz.py",), True),
        ("foo/bar/baz.py", ("foo/bar/*",), True),
        ("foo/bar/baz.py", (), False),
    ],
)
def test_file_matches_any_pattern(file_name: str, patterns: tuple[str, ...], expected_match: bool) -> None:
    assert file_matches_any_pattern(file_name, patterns) == expected_match

from copy import deepcopy
from unittest.mock import MagicMock

import pytest


class CopyingMock(MagicMock):
    """Mock which copies arguments when mocks are called with mutable arguments.

    https://docs.python.org/3/library/unittest.mock-examples.html#coping-with-mutable-arguments
    """

    def __call__(self, /, *args, **kwargs):
        args = deepcopy(args)
        kwargs = deepcopy(kwargs)
        return super().__call__(*args, **kwargs)


@pytest.fixture
def diffs_response() -> dict[str, object]:
    return {
        "base_commit_sha": "4d0e7ba86338590ba9937e58b6447f0e9ac9aff0",
        "commits": [
            {
                "author_email": "sergio.lara@elementsinteractive.es",
                "author_name": "Sergio Castillo",
                "authored_date": "2024-10-18T07:08:04.000Z",
                "committed_date": "2024-10-18T07:08:04.000Z",
                "committer_email": "sergio.lara@elementsinteractive.es",
                "committer_name": "Sergio Castillo",
                "created_at": "2024-10-18T07:08:04.000Z",
                "extended_trailers": {},
                "id": "6b1cfb66d9aa059b1089dfb836534ced292d4ea7",
                "message": "fix: solve lint config issues\n",
                "parent_ids": [],
                "short_id": "6b1cfb66",
                "title": "fix: solve lint config issues",
                "trailers": {},
                "web_url": "https://gitlab.com/namespace/lgtm/-/commit/6b1cfb66d9aa059b1089dfb836534ced292d4ea7",
            }
        ],
        "created_at": "2024-10-18T07:08:56.634Z",
        "diffs": [
            {
                "a_mode": "100644",
                "b_mode": "100644",
                "deleted_file": False,
                "diff": "@@ -45,7 +45,7 @@ format *files=target_dirs: venv\n"
                " # Lint all code in the project.\n"
                ' lint report="false": venv\n'
                "     {{ run }} ruff format --check {{ target_dirs }}\n"
                "-    {{ run }} ruff check {{ target_dirs }} {{ if report "
                '== "true" { "--format gitlab > '
                'tests/gl-code-quality-report.json" } else { "" } }}\n'
                "+    {{ run }} ruff check {{ target_dirs }} {{ if report "
                '== "true" { "--output-format gitlab > '
                'tests/gl-code-quality-report.json" } else { "" } }}\n'
                "     {{ run }} mypy {{ target_dirs }}\n"
                " \n"
                " # Serve the documentation in a local server.\n",
                "generated_file": False,
                "new_file": False,
                "new_path": "justfile",
                "old_path": "justfile",
                "renamed_file": False,
            },
            {
                "a_mode": "100644",
                "b_mode": "100644",
                "deleted_file": False,
                "diff": '@@ -75,7 +75,7 @@ convention = "pep257"\n'
                " [tool.ruff.lint.isort]\n"
                ' known-third-party = ["lgtm", "tests"]\n'
                " \n"
                "-[tool.ruff.per-file-ignores]\n"
                "+[tool.ruff.lint.per-file-ignores]\n"
                ' "tests/*" = [\n'
                '     "ANN", # no enforcement of type annotations in '
                "tests\n"
                '     "S",   # bandit is not useful in tests\n',
                "generated_file": False,
                "new_file": False,
                "new_path": "pyproject.toml",
                "old_path": "pyproject.toml",
                "renamed_file": False,
            },
        ],
        "head_commit_sha": "6b1cfb66d9aa059b1089dfb836534ced292d4ea7",
        "id": 1153558809,
        "merge_request_id": 334948343,
        "patch_id_sha": "5e35b8a16e0100ef1e783e5aeef8e12879a40258",
        "real_size": "2",
        "start_commit_sha": "4d0e7ba86338590ba9937e58b6447f0e9ac9aff0",
        "state": "collected",
    }

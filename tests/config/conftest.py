import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest


@contextmanager
def create_tmp_file(path: Path, data: str) -> Iterator[str]:
    path.write_text(data)
    try:
        yield str(path)
    finally:
        os.remove(path)


@pytest.fixture
def lgtm_toml_file(tmp_path: Path) -> Iterator[str]:
    pyproject_toml = tmp_path / "lgtm.toml"
    data = """
    technologies = ["perl", "javascript"]
    """
    with create_tmp_file(pyproject_toml, data) as tmp_file:
        yield tmp_file


@pytest.fixture
def invalid_toml_file(tmp_path: Path) -> Iterator[str]:
    invalid_toml = tmp_path / "invalid.toml"
    data = """
    in a whole in the ground ='there lived a hobbit"
    """
    with create_tmp_file(invalid_toml, data) as tmp_file:
        yield tmp_file

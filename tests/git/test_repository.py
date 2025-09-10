import pathlib
import tempfile
from collections.abc import Generator
from unittest import mock

import pytest
from lgtm_ai.git.exceptions import GitDiffParseError
from lgtm_ai.git.parser import DiffFileMetadata, DiffResult
from lgtm_ai.git.repository import (
    _extract_file_metadata,
    _get_diff_text,
    get_diff_from_local_repo,
    get_file_contents_from_local_repo,
)

import git


@pytest.fixture
def mock_repo() -> mock.Mock:
    """Mock git repository with controlled behavior."""
    repo = mock.Mock(spec=git.Repo)
    repo.active_branch.name = "feature-branch"
    repo.head.commit = mock.Mock()
    return repo


@pytest.fixture
def mock_diff_item() -> mock.Mock:
    """Mock git diff item with sample data."""
    diff_item = mock.Mock(spec=git.diff.Diff)
    diff_item.a_path = "old_file.py"
    diff_item.b_path = "new_file.py"
    diff_item.new_file = False
    diff_item.deleted_file = False
    diff_item.renamed_file = True
    diff_item.diff = b"@@ -1,3 +1,3 @@\n-old line\n+new line\n"
    return diff_item


@pytest.fixture
def temp_git_repo() -> Generator[pathlib.Path, None, None]:
    """Create a temporary git repository for integration tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = pathlib.Path(tmpdir)
        repo = git.Repo.init(repo_path)

        # Configure git user for commits
        repo.config_writer().set_value("user", "name", "Test User").release()
        repo.config_writer().set_value("user", "email", "test@example.com").release()

        # Create initial commit
        test_file = repo_path / "test.py"
        test_file.write_text("def hello():\n    return 'world'\n")
        repo.index.add(["test.py"])  # Use relative path
        repo.index.commit("Initial commit")

        yield repo_path


class TestGetDiffFromLocalRepo:
    """Test the main get_diff_from_local_repo function."""

    def test_invalid_repository_path(self) -> None:
        """Test error handling for invalid repository paths."""
        invalid_path = pathlib.Path("/nonexistent/path")

        with pytest.raises(GitDiffParseError, match="Cannot read local git repository"):
            get_diff_from_local_repo(invalid_path)

    @mock.patch("lgtm_ai.git.repository.git.Repo")
    def test_working_directory_changes_default(self, mock_repo_class: mock.Mock) -> None:
        """Test default behavior - working directory changes vs HEAD."""
        mock_repo = mock.Mock()
        mock_repo.active_branch.name = "main"
        mock_repo.head.commit.diff.return_value = []
        mock_repo_class.return_value = mock_repo

        result = get_diff_from_local_repo(pathlib.Path("/fake/path"))

        # Verify diff was called with None (working directory)
        mock_repo.head.commit.diff.assert_called_once_with(None, create_patch=True)
        assert result.target_branch == "HEAD"
        assert result.source_branch == "main"

    @mock.patch("lgtm_ai.git.repository.git.Repo")
    def test_compare_against_branch(self, mock_repo_class: mock.Mock) -> None:
        """Test comparing against a specific branch."""
        mock_repo = mock.Mock()
        mock_repo.active_branch.name = "feature"
        mock_compare_commit = mock.Mock()
        mock_repo.commit.return_value = mock_compare_commit
        mock_compare_commit.diff.return_value = []
        mock_repo_class.return_value = mock_repo

        result = get_diff_from_local_repo(pathlib.Path("/fake/path"), compare="main")

        # Verify correct commit was retrieved and diff called
        mock_repo.commit.assert_called_once_with("main")
        mock_compare_commit.diff.assert_called_once_with(mock_repo.head.commit, create_patch=True)
        assert result.target_branch == "main"
        assert result.source_branch == "feature"

    @mock.patch("lgtm_ai.git.repository.git.Repo")
    def test_invalid_compare_reference(self, mock_repo_class: mock.Mock) -> None:
        """Test error handling for invalid branch/commit references."""
        mock_repo = mock.Mock()
        mock_repo.commit.side_effect = git.exc.BadName("invalid-ref")
        mock_repo_class.return_value = mock_repo

        with pytest.raises(GitDiffParseError, match="Invalid branch/commit: invalid-ref"):
            get_diff_from_local_repo(pathlib.Path("/fake/path"), compare="invalid-ref")

    @mock.patch("lgtm_ai.git.repository.git.Repo")
    @mock.patch("lgtm_ai.git.repository.parse_diff_patch")
    @mock.patch("lgtm_ai.git.repository._extract_file_metadata")
    @mock.patch("lgtm_ai.git.repository._get_diff_text")
    def test_diff_processing(
        self,
        mock_get_diff_text: mock.Mock,
        mock_extract_metadata: mock.Mock,
        mock_parse_diff: mock.Mock,
        mock_repo_class: mock.Mock,
    ) -> None:
        """Test processing of diff items."""
        # Setup mocks
        mock_repo = mock.Mock()
        mock_repo.active_branch.name = "test-branch"
        mock_diff_item = mock.Mock()
        mock_repo.head.commit.diff.return_value = [mock_diff_item]
        mock_repo_class.return_value = mock_repo

        # Mock the helper functions
        mock_metadata = DiffFileMetadata(
            new_file=False, deleted_file=False, renamed_file=False, new_path="test.py", old_path=None
        )
        mock_extract_metadata.return_value = mock_metadata
        mock_get_diff_text.return_value = "diff text"
        mock_diff_result = DiffResult(metadata=mock_metadata, modified_lines=[])
        mock_parse_diff.return_value = mock_diff_result

        result = get_diff_from_local_repo(pathlib.Path("/fake/path"))

        # Verify all processing steps were called
        mock_extract_metadata.assert_called_once_with(mock_diff_item)
        mock_get_diff_text.assert_called_once_with(mock_diff_item)
        mock_parse_diff.assert_called_once_with(mock_metadata, "diff text")

        assert len(result.diff) == 1
        assert result.changed_files == ["test.py"]

    @pytest.mark.parametrize(
        ("compare", "expected_target"),
        [
            ("HEAD", "HEAD"),
            ("main", "main"),
            ("develop", "develop"),
            ("HEAD~1", "HEAD~1"),
            ("abc123", "abc123"),
        ],
    )
    @mock.patch("lgtm_ai.git.repository.git.Repo")
    def test_compare_parameter_values(self, mock_repo_class: mock.Mock, compare: str, expected_target: str) -> None:
        """Test various values for the compare parameter."""
        mock_repo = mock.Mock()
        mock_repo.active_branch.name = "current"

        if compare == "HEAD":
            mock_repo.head.commit.diff.return_value = []
        else:
            mock_compare_commit = mock.Mock()
            mock_repo.commit.return_value = mock_compare_commit
            mock_compare_commit.diff.return_value = []

        mock_repo_class.return_value = mock_repo

        result = get_diff_from_local_repo(pathlib.Path("/fake/path"), compare=compare)

        assert result.target_branch == expected_target
        assert result.source_branch == "current"


class TestGetFileContentsFromLocalRepo:
    """Test the get_file_contents_from_local_repo function."""

    def test_existing_file(self, temp_git_repo: pathlib.Path) -> None:
        """Test reading contents of existing file."""
        expected_content = "def hello():\n    return 'world'\n"

        result = get_file_contents_from_local_repo(temp_git_repo, pathlib.Path("test.py"))

        assert result == expected_content

    def test_nonexistent_file(self, temp_git_repo: pathlib.Path) -> None:
        """Test reading contents of non-existent file."""
        result = get_file_contents_from_local_repo(temp_git_repo, pathlib.Path("nonexistent.py"))

        assert result == ""

    def test_binary_file(self, temp_git_repo: pathlib.Path) -> None:
        """Test reading binary file returns empty string."""
        binary_file = temp_git_repo / "binary.bin"
        binary_file.write_bytes(b"\xff\xfe\x00\x00\x80\x81\x82")  # Invalid UTF-8 bytes

        result = get_file_contents_from_local_repo(temp_git_repo, pathlib.Path("binary.bin"))

        assert result == ""


class TestGetDiffText:
    """Test the _get_diff_text helper function."""

    def test_diff_as_bytes(self) -> None:
        """Test extracting diff text when it's bytes."""
        mock_diff = mock.Mock()
        mock_diff.diff = b"@@ -1,1 +1,1 @@\n-old\n+new"

        result = _get_diff_text(mock_diff)

        assert result == "@@ -1,1 +1,1 @@\n-old\n+new"

    def test_diff_as_string(self) -> None:
        """Test extracting diff text when it's already a string."""
        mock_diff = mock.Mock()
        mock_diff.diff = "@@ -1,1 +1,1 @@\n-old\n+new"

        result = _get_diff_text(mock_diff)

        assert result == "@@ -1,1 +1,1 @@\n-old\n+new"

    def test_no_diff(self) -> None:
        """Test extracting diff text when there's no diff."""
        mock_diff = mock.Mock()
        mock_diff.diff = None

        result = _get_diff_text(mock_diff)

        assert result == ""


class TestExtractFileMetadata:
    """Test the _extract_file_metadata helper function."""

    def test_renamed_file(self, mock_diff_item: mock.Mock) -> None:
        """Test extracting metadata for renamed file."""
        result = _extract_file_metadata(mock_diff_item)

        assert result.new_path == "new_file.py"
        assert result.old_path == "old_file.py"
        assert result.renamed_file is True
        assert result.new_file is False
        assert result.deleted_file is False

    def test_new_file(self) -> None:
        """Test extracting metadata for new file."""
        mock_diff = mock.Mock()
        mock_diff.a_path = None
        mock_diff.b_path = "new_file.py"
        mock_diff.new_file = True
        mock_diff.deleted_file = False
        mock_diff.renamed_file = False

        result = _extract_file_metadata(mock_diff)

        assert result.new_path == "new_file.py"
        assert result.old_path is None
        assert result.new_file is True

    def test_deleted_file(self) -> None:
        """Test extracting metadata for deleted file."""
        mock_diff = mock.Mock()
        mock_diff.a_path = "deleted_file.py"
        mock_diff.b_path = None
        mock_diff.new_file = False
        mock_diff.deleted_file = True
        mock_diff.renamed_file = False

        result = _extract_file_metadata(mock_diff)

        assert result.new_path == "deleted_file.py"
        assert result.old_path == "deleted_file.py"  # For deleted files, old_path should be set
        assert result.deleted_file is True

    def test_same_path_no_rename(self) -> None:
        """Test extracting metadata when file has same path (not renamed)."""
        mock_diff = mock.Mock()
        mock_diff.a_path = "same_file.py"
        mock_diff.b_path = "same_file.py"
        mock_diff.new_file = False
        mock_diff.deleted_file = False
        mock_diff.renamed_file = False

        result = _extract_file_metadata(mock_diff)

        assert result.new_path == "same_file.py"
        assert result.old_path is None  # Same path, so no old_path
        assert result.renamed_file is False

    def test_unknown_path_fallback(self) -> None:
        """Test fallback to 'unknown' when both paths are None."""
        mock_diff = mock.Mock()
        mock_diff.a_path = None
        mock_diff.b_path = None
        mock_diff.new_file = False
        mock_diff.deleted_file = False
        mock_diff.renamed_file = False

        result = _extract_file_metadata(mock_diff)

        assert result.new_path == "unknown"
        assert result.old_path is None

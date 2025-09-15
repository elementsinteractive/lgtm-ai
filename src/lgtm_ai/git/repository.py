import logging
import pathlib
import typing

from lgtm_ai.git.exceptions import GitDiffParseError, GitNotFoundError
from lgtm_ai.git.parser import DiffFileMetadata, DiffResult, parse_diff_patch
from lgtm_ai.git_client.schemas import PRDiff

if typing.TYPE_CHECKING:
    from git.diff import Diff

logger = logging.getLogger("lgtm")


def get_diff_from_local_repo(git_dir: pathlib.Path, *, compare: str = "HEAD") -> PRDiff:
    """Get git diff from a local repository and parse it into PRDiff format.

    Args:
        git_dir: Path to the git repository
        compare: What to compare against (branch name, commit hash, or "HEAD" for working dir changes)
    """
    try:
        import git
    except ImportError as e:
        raise GitNotFoundError(
            "Retrievig local diffs from git repository requires `git` to be available in the system PATH."
        ) from e

    try:
        repo = git.Repo(git_dir)
    except (git.InvalidGitRepositoryError, git.NoSuchPathError) as e:
        raise GitDiffParseError("Cannot read local git repository") from e

    current_branch = repo.active_branch.name

    # Get diff based on compare parameter
    if compare == "HEAD":
        # Working directory changes (git diff)
        diff_index = repo.head.commit.diff(None, create_patch=True)
        target_branch = "HEAD"
    else:
        # Compare current branch against specified compare (git diff compare..HEAD)
        try:
            compare_commit = repo.commit(compare)
            diff_index = compare_commit.diff(repo.head.commit, create_patch=True)
            target_branch = compare
        except git.BadName as e:
            raise GitDiffParseError(f"Invalid branch/commit: {compare}") from e

    # Parse each diff item
    diff_results: list[DiffResult] = []
    changed_files: list[str] = []

    for diff_item in diff_index:
        metadata = _extract_file_metadata(diff_item)
        changed_files.append(metadata.new_path)

        diff_text = _get_diff_text(diff_item)
        diff_result = parse_diff_patch(metadata, diff_text)
        diff_results.append(diff_result)

    return PRDiff(
        id=1,
        diff=diff_results,
        changed_files=changed_files,
        target_branch=target_branch,
        source_branch=current_branch,
    )


def get_file_contents_from_local_repo(git_dir: pathlib.Path, file_name: pathlib.Path) -> str:
    """Get the contents of a file from the local repository."""
    file_path = git_dir / file_name
    if not file_path.exists() or not file_path.is_file():
        logger.warning("File %s does not exist in the local repository", file_name)
        return ""
    try:
        return file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        logger.warning("File %s is not a utf-8 encoded text file", file_name)
        return ""


def _get_diff_text(diff_item: "Diff") -> str:
    """Extract diff text from a diff item."""
    if diff_item.diff:
        return diff_item.diff.decode("utf-8") if isinstance(diff_item.diff, bytes) else diff_item.diff
    return ""


def _extract_file_metadata(diff_item: "Diff") -> DiffFileMetadata:
    """Extract file metadata from GitPython diff item."""
    new_path = diff_item.b_path or diff_item.a_path or "unknown"
    old_path = diff_item.a_path if diff_item.a_path != diff_item.b_path else None

    return DiffFileMetadata(
        new_file=diff_item.new_file,
        deleted_file=diff_item.deleted_file,
        renamed_file=diff_item.renamed_file,
        new_path=new_path,
        old_path=old_path,
    )

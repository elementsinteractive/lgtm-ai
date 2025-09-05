import fnmatch
import pathlib

from lgtm_ai.base.schemas import PRSource


def file_matches_any_pattern(file_name: str, patterns: tuple[str, ...]) -> bool:
    for pattern in patterns:
        full_match = fnmatch.fnmatch(file_name, pattern)
        only_filename_match = fnmatch.fnmatch(pathlib.Path(file_name).name, pattern)
        matches = full_match or only_filename_match
        if matches:
            return True
    return False


def git_source_supports_multiline_suggestions(source: PRSource) -> bool:
    """Check if the given git source supports multiline suggestions.

    GitLab does support specifying suggestions that span multiple lines in single-line comments.
    GitHub requires the comment to be multi-line, and the suggestion does not need special markup with ranges.
    """
    return source == PRSource.gitlab

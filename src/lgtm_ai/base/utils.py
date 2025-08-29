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


def git_source_supports_suggestions(source: PRSource) -> bool:
    """For now, we only support suggestions in GitLab.

    TODO: https://github.com/elementsinteractive/lgtm-ai/issues/96
    """
    return source == PRSource.gitlab

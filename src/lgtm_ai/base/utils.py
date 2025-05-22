import fnmatch
import pathlib


def file_matches_any_pattern(file_name: str, patterns: tuple[str, ...]) -> bool:
    for pattern in patterns:
        full_match = fnmatch.fnmatch(file_name, pattern)
        only_filename_match = fnmatch.fnmatch(pathlib.Path(file_name).name, pattern)
        matches = full_match or only_filename_match
        if matches:
            return True
    return False

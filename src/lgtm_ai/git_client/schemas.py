from dataclasses import dataclass

from lgtm_ai.git_parser.parser import DiffResult


@dataclass(frozen=True, slots=True)
class PRDiff:
    id: int
    diff: list[DiffResult]
    changed_files: list[str]
    target_branch: str
    source_branch: str


@dataclass(frozen=True, slots=True)
class PRContextFileContents:
    file_path: str
    content: str


@dataclass(slots=True)
class PRContext:
    """Represents the context a reviewer might need when reviewing PRs.

    At the moment, it is just the contents of the files that are changed in the PR.
    """

    file_contents: list[PRContextFileContents]

    def __bool__(self) -> bool:
        return bool(self.file_contents)

    def add_file(self, file_path: str, content: str) -> None:
        self.file_contents.append(PRContextFileContents(file_path, content))


@dataclass(frozen=True, slots=True)
class PRMetadata:
    title: str
    description: str

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PRDiff:
    id: int
    diff: str
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

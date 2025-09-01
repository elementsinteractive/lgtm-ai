from lgtm_ai.git_client.schemas import ContextBranch
from pydantic import BaseModel


class PRContextFileContents(BaseModel):
    file_path: str
    content: str
    branch: ContextBranch = "source"


class PRCodeContext(BaseModel):
    """Represents the context a reviewer might need when reviewing PRs.

    At the moment, it is just the contents of the files that are changed in the PR.
    """

    file_contents: list[PRContextFileContents]

    def __bool__(self) -> bool:
        return bool(self.file_contents)

    def add_file(self, file_path: str, content: str, branch: ContextBranch = "source") -> None:
        self.file_contents.append(PRContextFileContents(file_path=file_path, content=content, branch=branch))

from unittest import mock

from lgtm_ai.ai.schemas import Review, ReviewGuide
from lgtm_ai.base.schemas import PRUrl
from lgtm_ai.git.parser import DiffFileMetadata, DiffResult, ModifiedLine
from lgtm_ai.git_client.base import GitClient
from lgtm_ai.git_client.schemas import ContextBranch, IssueContent, PRDiff, PRMetadata
from pydantic import HttpUrl
from pydantic_ai.usage import RunUsage

MOCK_USAGE = mock.MagicMock(
    requests=1, input_tokens=200, output_tokens=100, total_tokens=300, details={}, spec=RunUsage
)

MOCK_DIFF = [
    DiffResult(
        metadata=DiffFileMetadata(
            new_file=True,
            deleted_file=False,
            renamed_file=False,
            new_path="file1.txt",
            old_path=None,
        ),
        modified_lines=[
            ModifiedLine(line="contents-of-file1", line_number=2, relative_line_number=1, modification_type="removed")
        ],
    ),
    DiffResult(
        metadata=DiffFileMetadata(
            new_file=True,
            deleted_file=False,
            renamed_file=False,
            new_path="file2.txt",
            old_path=None,
        ),
        modified_lines=[
            ModifiedLine(line="contents-of-file2", line_number=20, relative_line_number=2, modification_type="removed")
        ],
    ),
]


class MockGitClient(GitClient):
    def get_diff_from_url(self, pr_url: PRUrl) -> PRDiff:
        return PRDiff(
            id=1,
            diff=MOCK_DIFF,
            changed_files=["file-1.txt", "file-2.txt"],
            target_branch="main",
            source_branch="feature",
        )

    def publish_review(self, pr_url: PRUrl, review: Review) -> None:
        return None

    def get_pr_metadata(self, pr_url: PRUrl) -> PRMetadata:
        return PRMetadata(title="feat(#288): a title", description="bar")

    def publish_guide(self, pr_url: PRUrl, guide: ReviewGuide) -> None:
        return None

    def get_issue_content(self, issues_url: HttpUrl, issue_id: str) -> IssueContent | None:
        return IssueContent(title="Issue title", description="Issue description")

    def get_file_contents(self, pr_url: PRUrl, file_path: str, branch_name: ContextBranch) -> str | None:
        return f"contents-of-{file_path}-context"

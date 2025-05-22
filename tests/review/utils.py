from lgtm_ai.ai.schemas import Review, ReviewGuide
from lgtm_ai.base.schemas import PRUrl
from lgtm_ai.git_client.base import GitClient
from lgtm_ai.git_client.schemas import PRContext, PRContextFileContents, PRDiff, PRMetadata
from lgtm_ai.git_parser.parser import DiffFileMetadata, DiffResult, ModifiedLine

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
        return PRDiff(1, MOCK_DIFF, changed_files=["file1", "file2"], target_branch="main", source_branch="feature")

    def publish_review(self, pr_url: PRUrl, review: Review) -> None:
        return None

    def get_context(self, pr_url: PRUrl, pr_diff: PRDiff) -> PRContext:
        return PRContext(
            file_contents=[
                PRContextFileContents(file_path="file1.txt", content="contents-of-file-1-context"),
                PRContextFileContents(file_path="file2.txt", content="contents-of-file-2-context"),
            ]
        )

    def get_pr_metadata(self, pr_url: PRUrl) -> PRMetadata:
        return PRMetadata(title="foo", description="bar")

    def publish_guide(self, pr_url: PRUrl, guide: ReviewGuide) -> None:
        return None

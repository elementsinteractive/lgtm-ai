from lgtm.git_parser.parser import DiffFileMetadata, DiffResult, ModifiedLine

PARSED_GIT_DIFF = [
    DiffResult(
        metadata=DiffFileMetadata(
            new_file=False, deleted_file=False, renamed_file=False, new_path="justfile", old_path="justfile"
        ),
        modified_lines=[
            ModifiedLine(
                line='    {{ run }} ruff check {{ target_dirs }} {{ if report == "true" { "--format gitlab > tests/gl-code-quality-report.json" } else { "" } }}',
                line_number=48,
                modification_type="removed",
            ),
            ModifiedLine(
                line='    {{ run }} ruff check {{ target_dirs }} {{ if report == "true" { "--output-format gitlab > tests/gl-code-quality-report.json" } else { "" } }}',
                line_number=48,
                modification_type="added",
            ),
        ],
    ),
    DiffResult(
        metadata=DiffFileMetadata(
            new_file=False, deleted_file=False, renamed_file=False, new_path="pyproject.toml", old_path="pyproject.toml"
        ),
        modified_lines=[
            ModifiedLine(line="[tool.ruff.per-file-ignores]", line_number=78, modification_type="removed"),
            ModifiedLine(line="[tool.ruff.lint.per-file-ignores]", line_number=78, modification_type="added"),
        ],
    ),
]

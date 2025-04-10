from lgtm.git_parser.parser import DiffFileMetadata, DiffResult, ModifiedLine

DUMMY_METADATA = DiffFileMetadata(
    new_file=True,
    deleted_file=False,
    renamed_file=False,
    new_path="example.txt",
    old_path="example.txt",
)

SIMPLE_DIFF = """@@ -45,7 +45,7 @@ format *files=target_dirs: venv
 # Lint all code in the project.
 lint report="false": venv
     {{ run }} ruff format --check {{ target_dirs }}
-    {{ run }} ruff check {{ target_dirs }} {{ if report == "true" { "--format gitlab > tests/gl-code-quality-report.json" } else { "" } }}
+    {{ run }} ruff check {{ target_dirs }} {{ if report == "true" { "--output-format gitlab > tests/gl-code-quality-report.json" } else { "" } }}
     {{ run }} mypy {{ target_dirs }}
"""


PARSED_SIMPLE_DIFF = DiffResult(
    metadata=DUMMY_METADATA,
    modified_lines=[
        ModifiedLine(
            line='    {{ run }} ruff check {{ target_dirs }} {{ if report == "true" { "--format gitlab > tests/gl-code-quality-report.json" } else { "" } }}',
            line_number=48,
            added=False,
        ),
        ModifiedLine(
            line='    {{ run }} ruff check {{ target_dirs }} {{ if report == "true" { "--output-format gitlab > tests/gl-code-quality-report.json" } else { "" } }}',
            line_number=48,
            added=True,
        ),
    ],
)


REFACTOR_DIFF = """@@ -10,7 +10,8 @@ def calculate_total(prices):
     total = 0
-    for p in prices:
-        total += p
+    for price in prices:
+        total += price
     return total
"""

PARSED_REFACTOR_DIFF = DiffResult(
    metadata=DUMMY_METADATA,
    modified_lines=[
        ModifiedLine(line="    for p in prices:", line_number=11, added=False),
        ModifiedLine(line="        total += p", line_number=12, added=False),
        ModifiedLine(line="    for price in prices:", line_number=11, added=True),
        ModifiedLine(line="        total += price", line_number=12, added=True),
    ],
)

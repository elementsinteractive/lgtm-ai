from lgtm_ai.git_parser.parser import DiffFileMetadata, DiffResult, ModifiedLine

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
            relative_line_number=4,
            modification_type="removed",
        ),
        ModifiedLine(
            line='    {{ run }} ruff check {{ target_dirs }} {{ if report == "true" { "--output-format gitlab > tests/gl-code-quality-report.json" } else { "" } }}',
            line_number=48,
            relative_line_number=5,
            modification_type="added",
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
        ModifiedLine(line="    for p in prices:", line_number=11, relative_line_number=2, modification_type="removed"),
        ModifiedLine(line="        total += p", line_number=12, relative_line_number=3, modification_type="removed"),
        ModifiedLine(
            line="    for price in prices:", line_number=11, relative_line_number=4, modification_type="added"
        ),
        ModifiedLine(line="        total += price", line_number=12, relative_line_number=5, modification_type="added"),
    ],
)

COMPLEX_DIFF_TEXT = '''
'@@ -2,7 +2,7 @@
 import logging
 from collections.abc import Callable
 from importlib.metadata import version
-from typing import get_args
+from typing import Any, assert_never, get_args

 import click
 import rich
@@ -13,10 +13,12 @@
     get_summarizing_agent_with_settings,
 )
 from lgtm_ai.ai.schemas import AgentSettings, CommentCategory, SupportedAIModels, SupportedAIModelsList
-from lgtm_ai.base.schemas import PRUrl
+from lgtm_ai.base.schemas import OutputFormat, PRUrl
 from lgtm_ai.config.handler import ConfigHandler, PartialConfig
+from lgtm_ai.formatters.base import Formatter
+from lgtm_ai.formatters.json import JsonFormatter
 from lgtm_ai.formatters.markdown import MarkDownFormatter
-from lgtm_ai.formatters.terminal import TerminalFormatter
+from lgtm_ai.formatters.pretty import PrettyFormatter
 from lgtm_ai.git_client.utils import get_git_client
 from lgtm_ai.review import CodeReviewer
 from lgtm_ai.review.guide import ReviewGuideGenerator
@@ -25,14 +27,15 @@
     parse_pr_url,
     validate_model_url,
 )
+from rich.console import Console
 from rich.logging import RichHandler

 __version__ = version("lgtm-ai")

 logging.basicConfig(
     format="%(message)s",
     datefmt="[%X]",
-    handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
+    handlers=[RichHandler(rich_tracebacks=True, show_path=False, console=Console(stderr=True))],
 )
 logger = logging.getLogger("lgtm")

@@ -68,6 +71,7 @@ def _common_options[**P, T](func: Callable[P, T]) -> Callable[P, T]:
         help="Exclude files from the review. If not provided, all files in the PR will be reviewed. Uses UNIX-style wildcards.",
     )
     @click.option("--publish", is_flag=True, help="Publish the review or guide to the git service.")
+    @click.option("--output-format", type=click.Choice([format.value for format in OutputFormat]))
     @click.option("--silent", is_flag=True, help="Do not print the review or guide to the console.")
     @click.option(
         "--ai-retries",
@@ -104,6 +108,7 @@ def review(
     config: str | None,
     exclude: tuple[str, ...],
     publish: bool,
+    output_format: OutputFormat | None,
     silent: bool,
     ai_retries: int | None,
     verbose: int,
@@ -125,6 +130,7 @@ def review(
             model=model,
             model_url=model_url,
             publish=publish,
+            output_format=output_format,
             silent=silent,
             ai_retries=ai_retries,
         ),
@@ -146,10 +152,10 @@ def review(

     if not resolved_config.silent:
         logger.info("Printing review to console")
-        terminal_formatter = TerminalFormatter()
-        rich.print(terminal_formatter.format_review_summary_section(review))
+        formatter, printer = _get_formatter_and_printer(resolved_config.output_format)
+        printer(formatter.format_review_summary_section(review))
         if review.review_response.comments:
-            rich.print(terminal_formatter.format_review_comments_section(review.review_response.comments))
+            printer(formatter.format_review_comments_section(review.review_response.comments))

     if resolved_config.publish:
         logger.info("Publishing review to git service")
@@ -168,6 +174,7 @@ def guide(
     config: str | None,
     exclude: tuple[str, ...],
     publish: bool,
+    output_format: OutputFormat | None,
     silent: bool,
     ai_retries: int | None,
     verbose: int,
@@ -184,6 +191,7 @@ def guide(
             ai_api_key=ai_api_key,
             model=model,
             publish=publish,
+            output_format=output_format,
             silent=silent,
             ai_retries=ai_retries,
         ),
@@ -203,8 +211,8 @@ def guide(

     if not resolved_config.silent:
         logger.info("Printing review to console")
-        terminal_formatter = TerminalFormatter()
-        rich.print(terminal_formatter.format_guide(guide))
+        formatter, printer = _get_formatter_and_printer(resolved_config.output_format)
+        printer(formatter.format_guide(guide))

     if resolved_config.publish:
         logger.info("Publishing review guide to git service")
@@ -220,3 +228,15 @@ def _set_logging_level(logger: logging.Logger, verbose: int) -> None:
     else:
         logger.setLevel(logging.DEBUG)
     logger.info("Logging level set to %s", logging.getLevelName(logger.level))
+
+
+def _get_formatter_and_printer(output_format: OutputFormat) -> tuple[Formatter[Any], Callable[[Any], None]]:
+    """Get the formatter and the print method based on the output format."""
+    if output_format == OutputFormat.pretty:
+        return PrettyFormatter(), rich.print
+    elif output_format == OutputFormat.markdown:
+        return MarkDownFormatter(), print
+    elif output_format == OutputFormat.json:
+        return JsonFormatter(), print
+    else:
+        assert_never(output_format)'
'''

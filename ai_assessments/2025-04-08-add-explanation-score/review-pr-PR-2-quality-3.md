# Review for PR: PR-2-quality

> Sample 3

> Using model: gpt-4o


🦉 **lgtm Review**

> **Score:** Nitpicks 🤓

**Summary:**

The PR enhances modularity and reusability by introducing a new formatter interface for handling review outputs. This is a solid change as it separates concerns, making it easier to maintain and extend formatter functionalities in the future. Two specific formatter strategies are implemented: Markdown and Terminal, which both conform to a common protocol. The inclusion of tests ensures that the formatters meet expected behavior, which is good practice for code changes.

Overall, the code quality is good, but there are a few minor issues that require attention to ensure consistent logic and code quality across the project. Here are the suggested improvements:

1. Ensure that unused imports are removed to keep the code clean.
2. Verify that the method `format_comments_section` in `TerminalFormatter` is consistent with its specification and behavior compared with `MarkDownFormatter`; the current implementation appears to have a potential discrepancy.
3. Address the redundancy in mock setup within test cases, potentially employing fixtures or helpers for repeated patterns.

Once these issues are addressed, the PR should be ready for merging.

**Specific Comments:**

- 🦉 **[Quality]** 🔵 `src/lgtm/__main__.py:8`




```python
from rich.panel import Panel
```


Remove this unused import since it's no longer being used in this script.

- 🦉 **[Quality]** 🟡 `src/lgtm/git_client/gitlab.py:31`




```python
logger.warning("Comments are not supported in the terminal formatter summary section")
```


While both `MarkDownFormatter` and `TerminalFormatter` handle comments, ensure that the behavior aligns with the intended design. The `TerminalFormatter` logs a warning when comments are included, while the `MarkDownFormatter` integrates them. This discrepancy might be worth clarifying or aligning if both should support comments similarly.

- 🦉 **[Quality]** 🔵 `tests/git_client/test_gitlab.py:23`




```python
def test_project_not_found_error() -> None:
m_client = mock.Mock()
```


Consider using a fixture for setting up common mock configurations across multiple tests. This will improve maintainability and readability of the test suite.
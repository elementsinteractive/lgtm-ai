# Review for PR: PR-2-quality

> Sample 1

> Using model: gemini-2.0-pro-exp-02-05


🦉 **lgtm Review**

> **Score:** Needs Work 🔧

**Summary:**

This PR introduces a new formatting system using a `ReviewFormatter` protocol, which is a good step towards separating concerns and improving code structure. The implementation includes formatters for Markdown and Terminal output, and existing code has been refactored to use this system.

However, there are a few issues that need addressing:
- A file seems to have been incorrectly moved from the `tests` directory into the `src` directory.
- Tests for the new `TerminalFormatter` appear to be missing.
- Some minor code quality improvements are suggested.

Please address these points before the PR can be merged.

**Specific Comments:**

- 🦉 **[Correctness]** 🔴 `src/lgtm/formatters/__init__.py:0`

This `__init__.py` file seems to have been moved from the `tests/test_git_client` directory into the `src/lgtm/formatters` directory. Test-related files should not be part of the source code distribution. Please revert this move or place the file in the correct test directory (`tests/formatters`).

- 🦉 **[Testing]** 🟡 `src/lgtm/formatters/terminal.py:13`




```python
class TerminalFormatter(ReviewFormatter[Panel | Layout]):
```


The PR introduces a `TerminalFormatter` but does not seem to include corresponding unit tests. Please add tests for `src/lgtm/formatters/terminal.py` to ensure its functionality is verified.

- 🦉 **[Quality]** 🔵 `scripts/evaluate_review_quality.py:90`




```python
    formatter = MarkDownFormatter()
```


The `MarkDownFormatter` is instantiated twice in this script (here and on line 78). While not critical, consider instantiating it once and reusing the instance for consistency and potential minor efficiency gains.
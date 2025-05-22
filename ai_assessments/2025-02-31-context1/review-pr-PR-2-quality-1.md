# Review for PR: PR-2-quality

> Sample 1

> Using model: gpt-4o


🦉 **lgtm Review**

> **Score:** Needs Some Work 🔧

**Summary:**

The changes in this pull request primarily focus on refactoring and introducing a formatter protocol for review comments, with specific implementations for Markdown and terminal outputs. The changes seem to provide a more standardized way to format and display review data both in GitLab and in the console.

Overall, the refactoring improves the separation of concerns and enhances flexibility and maintainability of the code by allowing different types of formatters, which can be beneficial for different output media.

Issues Identified:
1. **Duplicated Logic:** The `MarkDownFormatter` and `TerminalFormatter` have some overlapping logic for formatting summaries and comments. Consider abstracting the common logic, if applicable.
2. **Documentation:** Ensure classes and methods have adequate docstrings indicating their purpose and usage, especially for the formatters, to facilitate easier understanding and maintenance.
3. **Testing:** While there are tests for `MarkDownFormatter`, consider providing more comprehensive tests that include potential edge cases or invalid input scenarios.

In summary, the PR is well-structured and the intention behind the refactoring is clear, but it could benefit from additional abstraction and thorough documentation and test coverage improvements.

**Specific Comments:**

- 🦉 **[Quality]** 🔵 `src/lgtm/formatters/markdown.py:2` Consider adding a module-level docstring to explain the purpose of this module and its components.

- 🦉 **[Quality]** 🔵 `src/lgtm/formatters/markdown.py:21` Consider abstracting common logic in `format_summary_section` between different formatters to avoid duplication and potential inconsistencies.

- 🦉 **[Testing]** 🔵 `src/lgtm/formatters/markdown.py:33` Ensure there's a test case that covers instances where `comments` might be `None`. Test whether an empty string (instead of `"**Specific Comments:**"`) is returned in such cases.

- 🦉 **[Quality]** 🔵 `src/lgtm/formatters/base.py:2` Consider adding type hints and detailed docstrings to the methods within the protocol to clarify usage and expected behaviors.
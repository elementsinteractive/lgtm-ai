# Review for PR: PR-2-quality

> Sample 2

> Using model: gpt-4o


🦉 **lgtm Review**

> **Score:** Needs Some Work 🔧

**Summary:**

Overall, the PR introduces a significant refactoring by implementing a new system for formatting review summaries and comments for different outputs (Markdown and terminal). The refactoring is well-structured, enhancing the flexibility and maintainability of the code. It removes hard-coded formatting logic and replaces it with pluggable formatters, adhering to the Open/Closed principle of SOLID design. 

However, there are some areas that require attention:

1. **Category Import Modification**: The modification of category imports increases readability but should be followed consistently across all similar usages for uniformity.

2. **Mocking in Tests**: The tests use a mock formatter, which is good for isolating tests but consider testing more scenarios, especially edge cases.

3. **Logging**: In `TerminalFormatter`, comments are not supported in the summary section, and a warning is logged. It might be beneficial to handle this case more gracefully or remove logging if it's expected behavior.

Required changes:
1. Add more test coverage for edge cases in formatting logic, especially around comments.
2. Review logging usage in `TerminalFormatter` and decide its necessity.


**Specific Comments:**

- 🦉 **[Quality]** 🔵 `src/lgtm/ai/schemas.py:10` The refactoring here improves the readability and reusability of literals. It makes it easier to maintain and update categories and severity levels.

- 🦉 **[Quality]** 🔵 `src/lgtm/formatters/terminal.py:11` Logging a warning for a not supported feature in TerminalFormatter. If this is an expected scenario, consider handling it differently without a warning or provide a more informative message. This will reduce noise in the logs.

- 🦉 **[Testing]** 🟡 `tests/formatters/test_markdown.py:0` Test coverage is good for basic scenarios. Consider adding more edge cases, like handling special characters or extremely long comments.
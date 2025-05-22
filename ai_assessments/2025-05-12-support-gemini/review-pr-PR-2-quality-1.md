# Review for PR: PR-2-quality

> Sample 1

> Using model: gemini-2.0-pro-exp-02-05


🦉 **lgtm Review**

> **Score:** LGTM 👍

**Summary:**

This PR introduces a `ReviewFormatter` abstraction to handle different output formats (Markdown, Terminal) for the review results. The implementation is clean, uses protocols and constants effectively, and improves the separation of concerns by moving formatting logic out of the AI schemas and Git client.

The changes are well-tested, with new tests added for the formatters and existing tests updated accordingly.

Overall, this is a high-quality refactoring effort, and the code is ready to be merged.
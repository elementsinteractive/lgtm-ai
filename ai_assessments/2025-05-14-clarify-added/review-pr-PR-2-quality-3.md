# Review for PR: PR-2-quality

> Sample 3

> Using model: gpt-4.1


🦉 **lgtm Review**

> **Score:** LGTM 👍

**Summary:**

This PR refactors the formatting logic by decoupling Markdown and terminal formatters from the GitLab client and main scripts. This change improves the code's maintainability and separation of concerns, laying a solid foundation for future extensibility (e.g., adding GitHub or other formatters). The new formatter interface is well-documented, and the update across both production and test code shows thoroughness. Most issues are stylistic or suggestions for future enhancements. Please see the specific comments below for minor refinement opportunities. Overall, this is a high-quality PR and is ready to be merged after considering the minor suggestions.

**Specific Comments:**

- 🦉 **[Quality]** 🔵 `src/lgtm/ai/schemas.py:5`




```python
from pydantic import BaseModel, Field
```


There is now a redundant import of 'computed_field' in this module after refactoring to rely on formatters. Consider removing 'computed_field' if it is not used elsewhere to tidy up imports.

- 🦉 **[Quality]** 🔵 `src/lgtm/formatters/terminal.py:15`




```python
if comments:
    logger.warning("Comments are not supported in the terminal formatter summary section")
```


The 'format_summary_section' method logs a warning if comments are passed but does not display them in the terminal. This is appropriate, but in more advanced terminal UIs, supporting context comments could be considered in the future.

- 🦉 **[Quality]** 🔵 `src/lgtm/formatters/markdown.py:29`




```python
return "\n\n".join(lines)
```


The Markdown formatter adds double newlines between comment items for spacing. This is a stylistic choice; consider making the spacing configurable if readability or compactness becomes a concern for large outputs.
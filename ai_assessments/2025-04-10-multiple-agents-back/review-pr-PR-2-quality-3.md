# Review for PR: PR-2-quality

> Sample 3

> Using model: gpt-4o


🦉 **lgtm Review**

> **Score:** Nitpicks 🤓

**Summary:**

The PR enhances the LGTM reviews by introducing a new formatting system, which includes Markdown and Terminal formatters. This update significantly improves the structure and reusability of code by encapsulating the formatting logic into specific classes and constants. The use of typing, plugin protocols, and immutable constants like Final enhances the code's maintainability. However, while the provided tests for formatter classes are beneficial, there is room to strengthen the testing strategy, specifically around edge cases and exception handling.

**Specific Comments:**

- 🦉 **[Testing]** 🟡 `src/lgtm/formatters/base.py:1`




```Python
class ReviewFormatter(Protocol[_T]):
```


Ensure all public methods in `ReviewFormatter` are covered by tests. Consider adding tests with incomplete or incorrect data inputs to evaluate robust error handling.
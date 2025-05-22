# Review for PR: PR-2-quality

> Sample 2

> Using model: gpt-4.1


🦉 **lgtm Review**

> **Score:** LGTM 👍

**Summary:**

This PR introduces a flexible and extensible formatting subsystem for LGTM review output, with clear separation of concerns and robust type safety. Markdown and terminal formatters are now implemented via a protocol/interface-based approach. The refactor is thorough, and tests cover the new formatters and their integration. There are no correctness, testing, or security issues. The only point for improvement is minor: leftover references and comments to old formatting properties ('formatted_severity' and 'formatted_score') in the models (src/lgtm/ai/schemas.py) should be removed now that all formatting concerns are managed by the new formatter system. This is a low-severity maintainability issue. Overall, the PR is of high quality and ready to merge after optional cleanup.

**Specific Comments:**

- 🦉 **[Quality]** 🔵 `src/lgtm/ai/schemas.py:20`




```python
    @property
    def formatted_severity(self) -> str:
        emoji = {
            "LOW": "🟢",
            "MEDIUM": "🟡",
            "HIGH": "🔴",
        }
        return f"{emoji[self.severity]}"

    @property
    def formatted_score(self) -> str:
        emoji = {
            "LGTM": "👍",
            "Nitpicks": "🤓",
            "Needs Some Work": "🔧",
            "Needs a Lot of Work": "🚨",
        }
        return f"{self.score} {emoji[self.score]}"
```


Remove dead code and comments referencing 'formatted_severity' and 'formatted_score' properties, as all formatting is now handled by the formatter classes. Cleaning this improves maintainability and clarity.
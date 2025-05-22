# Review for PR: PR-2-quality

> Sample 2

> Using model: gpt-4o


🦉 **lgtm Review**

> **Score:** LGTM 👍

**Summary:**

The Pull Request (PR) introduces a more modular and testable code structure by implementing a formal "formatter" pattern across different files, with the introduction of `MarkDownFormatter` and `TerminalFormatter` classes. The PR is generally well-organized, effectively adding test coverage for new functionalities. This signifies a notable enhancement in the separation of concerns and adaptability of the code for diverse output formats.

A minor issue is identified concerning redundancy in emoji mappings for severity and scores found in both `src/lgtm/ai/schemas.py` and `src/lgtm/formatters/constants.py`. Consolidating these mappings in a single location would improve maintainability and coherence of the codebase.

Overall, the PR demonstrates quality improvements with appropriate testing incorporated, ensuring the robustness of the code changes. Addressing the aforementioned minor issue would further enhance the code maintainability and readability, but does not significantly impact the quality of the changes made.

**Specific Comments:**

- 🦉 **[Quality]** 🔵 `src/lgtm/ai/schemas.py:23`




```python
"LOW": "\ud83d\udfe2","MEDIUM": "\ud83d\udfe1","HIGH": "\ud83d\udd34"
```


Consider consolidating the emoji mappings in `src/lgtm/formatters/constants.py` by moving them from `src/lgtm/ai/schemas.py`. This will reduce redundancy and enhance maintainability.
# Review for PR: PR-2-quality

> Sample 1

> Using model: gpt-4o


🦉 **lgtm Review**

> **Score:** Nitpicks 🤓

**Summary:**

This pull request primarily focuses on introducing new formatters for both Markdown and Terminal outputs, alongside corresponding tests. The GitlabClient is now using these formatters for publishing reviews and comments, ensuring a more structured output. Additionally, the PR includes a refinement of data classes and literals to improve type safety and clarity in the codebase. However, a few areas need improvement: centralizing the redundant constants for maintainability, addressing redundant code, and ensuring consistent naming conventions. There is also a need to consider potential security implications regarding API key management.

Please address the detailed comments for specific guidance on code improvements.

**Specific Comments:**

- 🦉 **[Quality]** 🔵 `src/lgtm/ai/schemas.py:5`




```python
CommentCategory = Literal["Correctness", "Quality", "Testing"]
CommentSeverity = Literal["LOW", "MEDIUM", "HIGH"]
```


The redundancy in defining categories and severities as Literals multiple times can be avoided by defining them once and reusing them throughout the schema. This will enhance maintainability and clarity.

- 🦉 **[Quality]** 🔵 `scripts/evaluate_review_quality.py:90`




```python
formatter = MarkDownFormatter()
```


The instantiation of `formatter` as `MarkDownFormatter()` at line 90 is redundant since it is already set via the constructor of `GitlabClient`. Remove this redundant instantiation to improve code clarity.

- 🦉 **[Quality]** 🔵 `src/lgtm/formatters/constants.py:5`




```python
SEVERITY_MAP: Final[dict[CommentSeverity, str]] = {
    "LOW": "🔵",
    "MEDIUM": "🟡",
    "HIGH": "🔴",
}
```


The SEVERITY_MAP and SCORE_MAP constants are repeated across the codebase where the same emoji mappings are utilized. It is advised to centralize these constants so that all usages can pull from the same source, improving maintainability.
# Review for PR: PR-2-quality

> Sample 1

> Using model: gpt-4o


🦉 **lgtm Review**

> **Score:** Needs Some Work 🔧

**Summary:**

The PR introduces a more structured and modular approach by implementing formatters for handling review results in different display formats, such as Markdown and Terminal. It removes the in-line formatting logic that was previously in several different locations and replaces it with structured calls to formatters based on the type of output desired. The introduction of `ReviewFormatter` as a protocol for formatting reviews and specific implementations like `MarkDownFormatter` and `TerminalFormatter` enhances flexibility and adherence to open/closed principles.

Positive points:
- The refactor makes the codebase cleaner and more maintainable, focusing on separation of concerns.
- New tests have been added for the newly introduced formatters, which is crucial for long-term maintenance.

However, some issues need to be addressed:

1. **Correctness:** The `_format_score` method in the `MarkDownFormatter` class should handle unknown scores more gracefully. Currently, if an unknown score is passed, it will cause a KeyError. Handling such cases with a default value would make the implementation more robust.
2. **Quality:** Consider using helper methods or properties for repeated logic, such as the construction of panel arguments in `TerminalFormatter`.

Overall, the PR reflects a strong understanding of the task and coding standards. Once the specified changes are addressed, it should be ready for merging.

**Specific Comments:**

- 🦉 **[Correctness]** 🔴 `src/lgtm/formatters/markdown.py:33`




```python
def _format_score(self, score: ReviewScore) -> str:
    return f"{score} {SCORE_MAP[score]}"
```


The `_format_score` method in the `MarkDownFormatter` class should handle cases where an unknown score is passed. This will prevent a potential `KeyError` if the `review.review_response.score` contains an unexpected value. Consider using `SCORE_MAP.get(score, "Unknown Score")` as a fallback.

- 🦉 **[Quality]** 🔵 `src/lgtm/formatters/terminal.py:24`




```python
return Panel(
    Markdown(review.review_response.summary),
    title="🦉 lgtm Review",
    style="white",
    title_align="left",
    padding=(1, 1),
    subtitle=f"Score: {review.review_response.score} {SCORE_MAP[review.review_response.score]}",
)
```


Consider using a helper method to construct the `Panel` arguments that are repeated, which could improve readability and maintainability. This aligns with the DRY principle as some arguments are used multiple times for constructing panels.
# Review for PR: PR-2-quality

> Sample 1

> Using model: gemini-2.5-pro-preview-05-06


🦉 **lgtm Review**

> **Score:** Needs Work 🔧

**Summary:**

Overall, this PR is a good refactoring effort that successfully decouples formatting logic from the git client and main application logic. The introduction of the `ReviewFormatter` protocol and separate formatter implementations (Markdown, Terminal) improves modularity, maintainability, and extensibility. Constants are now centralized, and schemas have been cleaned up. Tests for the new Markdown formatter have been added, and existing tests are updated.

The main area for improvement is adding test coverage for the new `TerminalFormatter`, which is essential for ensuring its reliability. Additionally, a small enhancement to the `CommentCategory` definition is suggested for broader applicability.

**Specific Comments:**

- 🦉 **[Testing]** 🟡 `src/lgtm/formatters/terminal.py:13`




```python
class TerminalFormatter(ReviewFormatter[Panel | Layout]):
    def format_summary_section(self, review: Review, comments: list[ReviewComment] | None = None) -> Panel:
        if comments:
            logger.warning("Comments are not supported in the terminal formatter summary section")

        return Panel(
            Markdown(review.review_response.summary),
            title="
ud83e

udd89 lgtm Review",
            style="white",
            title_align="left",
            padding=(1, 1),
            subtitle=f"Score: {review.review_response.score} {SCORE_MAP[review.review_response.score]}",
        )

    def format_comments_section(self, comments: list[ReviewComment]) -> Layout:
        panels = [self.format_comment(comment) for comment in comments]
        layout = Layout()
        layout.split_column(*panels)
        return layout

    def format_comment(self, comment: ReviewComment) -> Panel:
        return Panel(
            comment.comment,
            title=f"{comment.new_path}:{comment.line_number}",
            subtitle=f"[{comment.category}] {SEVERITY_MAP[comment.severity]}",
            style="blue",
            title_align="left",
            subtitle_align="left",
            padding=(1, 1),
        )
```


The new `TerminalFormatter` class in `src/lgtm/formatters/terminal.py` introduces logic for formatting reviews for console output using the `rich` library. However, tests for this formatter have not been added in this PR. To ensure its correctness and prevent regressions, please add unit tests covering the different formatting methods (`format_summary_section`, `format_comments_section`, `format_comment`) of the `TerminalFormatter`.

- 🦉 **[Quality]** 🔵 `src/lgtm/ai/schemas.py:7`




```python
CommentCategory = Literal["Correctness", "Quality", "Testing"]
```


The `CommentCategory` literal currently includes "Correctness", "Quality", and "Testing". If the `lgtm` tool is intended to process or categorize review comments related to security, consider adding "Security" to this Literal type for consistency with common review categories and potentially broader alignment. This would ensure all expected comment types can be formally represented.

Suggestion:
```python
CommentCategory = Literal["Correctness", "Quality", "Testing", "Security"]
```

<details><summary>More information about this review</summary>

- **Review id**: `ed554bd1003f4cc0afa8cb102b3f1f5e`
- **Model**: `gemini-2.5-pro-preview-05-06`
- **Reviewed at**: `2025-05-15T15:52:44.169800+00:00`

> See the [📚 lgtm documentation](https://makerstreet-development.gitlab.io/elements/tools/lgtm) for more information about lgtm.

</details>

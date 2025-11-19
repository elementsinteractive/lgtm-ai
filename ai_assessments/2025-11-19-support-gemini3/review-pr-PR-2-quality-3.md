# Review for PR: PR-2-quality

> Sample 3

> Using model: gemini-3-pro-preview


## 🦉 lgtm Review

> **Score:** Nitpicks 🤓

### 🔍 Summary

This is a great refactor that improves the modularity of the code by decoupling formatters from the client logic.

However, there are a few gaps in testing that should be addressed:
1. The new `TerminalFormatter` lacks test coverage.
2. The `MockFormatter` used in `GitlabClient` tests is too loose; it doesn't verify that comments are correctly passed to the formatter, which could hide regressions.

Once these testing issues are resolved, the PR will be in excellent shape.


**Specific Comments:**

- #### 🦉 🧪 Testing

> **Severity:** MEDIUM 🟡


`````python
    def format_summary_section(self, review: Review, comments: list[ReviewComment] | None = None) -> str:
        return f"summary section {review.review_response.summary}"
`````


The `MockFormatter.format_summary_section` implementation ignores the `comments` argument. This means the test `test_post_review_with_a_successful_and_an_unsuccessful_comments` cannot distinguish whether `failed_comments` are correctly passed to the formatter or if an empty list is passed.

Please update the mock to include the comments (or their count) in the return value to ensure the data flow is verified.



`````suggestion
    def format_summary_section(self, review: Review, comments: list[ReviewComment] | None = None) -> str:
        suffix = f" with {len(comments)} comments" if comments else ""
        return f"summary section {review.review_response.summary}{suffix}"
`````




- #### 🦉 🧪 Testing

> **Severity:** MEDIUM 🟡


`````python
class TerminalFormatter(ReviewFormatter[Panel | Layout]):
`````


You added `TerminalFormatter` but there seem to be no tests covering it. Even if it relies on `rich` for rendering, it would be good to have a test ensuring it returns the expected `Panel`/`Layout` structure and doesn't crash.








<details><summary>More information</summary>

- **Id**: `59b19777169d4da3938b35c41ffd03b2`
- **Model**: `gemini-3-pro-preview`
- **Created at**: `2025-11-19T09:16:07.118224+00:00`


<details><summary>Usage summary</summary>

- **Request count**: `2`
- **Request tokens**: `76,379`
- **Response tokens**: `11,001`
- **Total tokens**: `87,380`

</details>


> See the [📚 lgtm-ai repository](https://github.com/elementsinteractive/lgtm-ai) for more information about lgtm.

</details>

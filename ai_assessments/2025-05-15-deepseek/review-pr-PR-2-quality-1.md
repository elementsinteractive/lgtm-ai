# Review for PR: PR-2-quality

> Sample 1

> Using model: deepseek-chat


🦉 **lgtm Review**

> **Score:** Nitpicks 🤓

**Summary:**

The PR refactors the formatters out of the client and main logic, separating markdown formatting from GitLab logic. The changes are well-structured and improve modularity. There are a few minor issues related to code quality, such as unused methods and docstring inconsistencies, but these do not impact functionality. The PR is almost ready to be merged after addressing these small improvements.

**Specific Comments:**

- 🦉 **[Quality]** 🔵 `src/lgtm/git_client/gitlab.py:120`




```python
def _get_summary_body(self, review: Review, failed_comments: list[ReviewComment]) -> str:
```


The `_get_summary_body` method is no longer used but remains in the code. It should be removed to avoid dead code.

- 🦉 **[Quality]** 🔵 `src/lgtm/formatters/markdown.py:34`




```python
def _format_score(self, score: ReviewScore) -> str:
```


The `_format_score` method is a private helper but is not marked as such with a leading underscore in its docstring. Consider updating the docstring to reflect its private nature.

- 🦉 **[Quality]** 🔵 `src/lgtm/__main__.py:78`




```python
def _print_review_to_console(review: Review) -> None:
```


The `_print_review_to_console` function is no longer used but remains in the code. It should be removed to avoid dead code.

<details><summary>More information about this review</summary>

- **Review id**: `1dad3b21785f472ca339c01da8cd0fc3`
- **Model**: `deepseek-chat`
- **Reviewed at**: `2025-05-15T15:22:06.393338+00:00`

> See the [📚 lgtm documentation](https://makerstreet-development.gitlab.io/elements/tools/lgtm) for more information about lgtm.

</details>

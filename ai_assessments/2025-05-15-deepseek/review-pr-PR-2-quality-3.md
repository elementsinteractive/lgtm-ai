# Review for PR: PR-2-quality

> Sample 3

> Using model: deepseek-chat


🦉 **lgtm Review**

> **Score:** Nitpicks 🤓

**Summary:**

The PR refactors the formatters out of the client and main logic, improving modularity and reusability. The changes are well-structured and adhere to clean code principles. There are a few minor issues related to error handling and type safety, but they do not significantly impact the overall quality of the PR. The PR is almost ready to be merged, with only minor improvements needed.

**Specific Comments:**

- 🦉 **[Correctness]** 🟡 `scripts/evaluate_review_quality.py:30`




```python
click.echo("You are on the main branch. Please checkout a feature branch to run this script.")
click.Abort()
```


The `click.Abort()` call should be replaced with `raise click.Abort()` to properly terminate the script when the branch is 'main'.

- 🦉 **[Quality]** 🔵 `src/lgtm/git_client/gitlab.py:120`




```python
def _get_summary_body(self, review: Review, failed_comments: list[ReviewComment]) -> str:
```


The `_get_summary_body` method is no longer used after the refactor and should be removed to avoid dead code.

- 🦉 **[Quality]** 🔵 `src/lgtm/formatters/markdown.py:34`




```python
def _format_score(self, score: ReviewScore) -> str:
```


The `_format_score` method could be made private by prefixing it with a single underscore (`_format_score`) to indicate it's for internal use only.

<details><summary>More information about this review</summary>

- **Review id**: `4e71e685a56e4d9cb9f836876e1bccf2`
- **Model**: `deepseek-chat`
- **Reviewed at**: `2025-05-15T15:24:36.846862+00:00`

> See the [📚 lgtm documentation](https://makerstreet-development.gitlab.io/elements/tools/lgtm) for more information about lgtm.

</details>

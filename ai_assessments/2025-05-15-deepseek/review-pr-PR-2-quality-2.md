# Review for PR: PR-2-quality

> Sample 2

> Using model: deepseek-chat


🦉 **lgtm Review**

> **Score:** Nitpicks 🤓

**Summary:**

The PR refactors the formatters out of the client and main logic, separating markdown formatting from GitLab logic. The changes are well-structured and improve modularity. There are a few minor issues to address, primarily around edge cases and logging, but overall the PR is in good shape.

**Specific Comments:**

- 🦉 **[Correctness]** 🟡 `src/lgtm/formatters/markdown.py:18`




```python
summary = header + review.review_response.summary
```


The `format_summary_section` method in `MarkDownFormatter` does not handle the case where `review.review_response.summary` is `None`. This could lead to a `TypeError` when concatenating strings. Consider adding a check for `None` or providing a default value. For example:
```python
summary = header + (review.review_response.summary or "No summary provided.")
```

- 🦉 **[Quality]** 🔵 `src/lgtm/git_client/gitlab.py:118`




```python
except gitlab.exceptions.GitlabError:
    # Add it to the list of failed comments to be published in the summary comment
    failed_comments.append(review_comment)
```


The `_post_comments` method in `GitlabClient` does not log the specific error when a comment fails to post. This makes debugging harder. Consider logging the error message from `GitlabError` to provide more context. For example:
```python
except gitlab.exceptions.GitlabError as e:
    logger.error(f"Failed to post comment: {e}")
    failed_comments.append(review_comment)
```

- 🦉 **[Quality]** 🔵 `src/lgtm/formatters/terminal.py:16`




```python
if comments:
    logger.warning("Comments are not supported in the terminal formatter summary section")
```


The `TerminalFormatter` class logs a warning when comments are provided to `format_summary_section`, but it does not include the comments in the output. This could be confusing for users. Either include the comments or update the warning message to clarify that comments are ignored. For example:
```python
logger.warning("Comments are not supported in the terminal formatter summary section and will be ignored.")
```

<details><summary>More information about this review</summary>

- **Review id**: `a84aee3efa9647d6aa4c389f3ae2f167`
- **Model**: `deepseek-chat`
- **Reviewed at**: `2025-05-15T15:23:31.524713+00:00`

> See the [📚 lgtm documentation](https://makerstreet-development.gitlab.io/elements/tools/lgtm) for more information about lgtm.

</details>

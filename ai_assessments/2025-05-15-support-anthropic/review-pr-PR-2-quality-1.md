# Review for PR: PR-2-quality

> Sample 1

> Using model: claude-3-5-sonnet-latest


🦉 **lgtm Review**

> **Score:** Nitpicks 🤓

**Summary:**

This PR implements a good refactoring of the formatters into separate reusable components. The code is clean, well-organized and follows good Python practices, moving formatting logic out of the client and main code into dedicated modules. The changes are well tested and the architecture allows for future extensibility (e.g. GitHub integration as mentioned in the PR description). There are just a few minor issues that could be improved, but the PR is almost ready to be merged.

**Specific Comments:**

- 🦉 **[Correctness]** 🟡 `src/lgtm/ai/schemas.py:7`




```python
CommentCategory = Literal["Correctness", "Quality", "Testing"]
```


Security should be included in the comment categories since it's one of the supported types in the CI/CD pipeline. Consider adding `"Security"` to the `CommentCategory` literal type:
```python
CommentCategory = Literal["Correctness", "Quality", "Testing", "Security"]
```

- 🦉 **[Testing]** 🔵 `tests/git_client/test_gitlab.py:202`




```python
"body": mock.ANY,
```


The test lacks verification of the actual comment content. While mock.ANY is used for flexibility, consider adding at least some basic content verification to ensure the formatting is working as expected.
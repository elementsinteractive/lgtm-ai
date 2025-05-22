# Review for PR: PR-2-quality

> Sample 3

> Using model: gpt-4o


🦉 **lgtm Review**

> **Score:** Nitpicks 🤓

**Summary:**

The PR focuses on enhancing the flexibility and format of review outputs by introducing Markdown and Terminal formatters, integrating them with the existing GitlabClient and other processes. It also maps severity and review scores to emoji for better visual representation. The code overall is of good quality, but there are minor issues regarding consistency and test coverage. It is suggested to improve naming conventions consistency, ensure that the integration of new formatters does not overload the constructor's responsibilities, and add tests for edge cases in the markdown formatter.

**Specific Comments:**

- 🦉 **[Quality]** 🔵 `src/lgtm/git_client/gitlab.py:25`




```python
def __init__(self, client: gitlab.Gitlab, formatter: ReviewFormatter[str]) -> None:
```


The constructor of `GitlabClient` now includes a `formatter` parameter. Ensure that the responsibilities of the client remain consistent. Overloading the constructor with such parameters can make the class harder to manage if more formatters are introduced in the future. Consider refactoring to maintain single responsibility.
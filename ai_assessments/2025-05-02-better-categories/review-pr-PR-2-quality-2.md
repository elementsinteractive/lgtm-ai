# Review for PR: PR-2-quality

> Sample 2

> Using model: gpt-4o


🦉 **lgtm Review**

> **Score:** Nitpicks 🤓

**Summary:**

The recent update introduces a new markdown formatter, enhancing the organization and readability of review outputs. Several formatter components and accompanying tests have been incorporated to ensure robust functionality and coverage. However, a few consistency issues need to be addressed, namely in harmonizing the use of the `formatter` variable across files to maintain uniformity. Also, ensure all potential `ReviewScore` literals are adequately mapped to prevent any unintended behavior. The testing section should explicitly define the expected calls instead of using `mock.ANY` for clarity and improved debugging. Overall, the PR is solid but requires addressing these minor issues for a seamless integration.

**Specific Comments:**

- 🦉 **[Quality]** 🔵 `scripts/evaluate_review_quality.py:90`




```python
formatter = MarkDownFormatter()
```


Refactor tests and implementations to consistently use the `formatter` variable name instead of directly instantiating `MarkDownFormatter` across different functions to improve code consistency and maintainability. 

```
formatter = MarkDownFormatter()
```


- 🦉 **[Correctness]** 🔵 `src/lgtm/ai/schemas.py:7`




```python
CommentCategory = Literal["Correctness", "Quality", "Testing"]
```


Ensure that the new type (`CommentCategory`) is properly integrated and its usage aligns with how comments are categorized elsewhere in the project to maintain consistency and robust type evaluation.

```
CommentCategory = Literal["Correctness", "Quality", "Testing"]
```


- 🦉 **[Testing]** 🔵 `tests/git_client/test_gitlab.py:116`




```python
"body": mock.ANY
```


While using mock's `ANY` is appropriate, consider explicitly defining what the expected calls should be for clearer understanding and debugging.

```
"body": mock.ANY
```


- 🦉 **[Correctness]** 🔵 `src/lgtm/formatters/markdown.py:34`




```python
def _format_score(self, score: ReviewScore) -> str:
```


In the `_format_score` function, ensure all potential `ReviewScore` literals are covered to prevent unexpected behavior. This ensures robustness in score-icon mappings.

```
def _format_score(self, score: ReviewScore) -> str:
```

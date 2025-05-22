# Review for PR: PR-2-quality

> Sample 1

> Using model: gpt-4o


🦉 **lgtm Review**

> **Score:** Nitpicks 🤓

**Summary:**

The PR enhances the review system by introducing new formatting options, such as markdown and terminal outputs, using the `ReviewFormatter` protocol. This allows for customizable review displays and removes code duplication. The existing emoji formatting from `ReviewComment` is now managed by formatters, making the code cleaner. Tests are updated to align with the new formatter system. However, some minor areas need improvement, such as ensuring consistent logging messages for better context during failures and considering additional tests for edge case scenarios like empty reviews.

While the changes are generally positive, there is a medium-severity issue regarding the `write_review_to_dir` function, which may not consistently reflect the review's state in cases of errors or failed comment posts. Addressing this and adding the suggested tests would refine the PR further before merging.

**Specific Comments:**

- 🦉 **[Correctness]** 🟡 `scripts/evaluate_review_quality.py:86`




```python
def write_review_to_dir(model: ChatModel, output_directory: str, pr_name: str, sample: int, review: Review) -> None:...
```


The `write_review_to_dir` method writes the review to a markdown file, but if there's an error in the review or if comments fail to post, it might not be accurately reflected in the output. Consider handling exceptions and ensuring the final state of the review is consistent with the PR's actual state.
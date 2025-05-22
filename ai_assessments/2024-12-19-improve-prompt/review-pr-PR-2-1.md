# Review for PR: PR-2

> Sample 1

## Summary

> The code introduces a logging system for better traceability and debugging while maintaining clarity. It seems to improve error handling by creating a custom exception class (`LGMTException`) and utilizes logging throughout the codebase for important events and error states. However, a few areas are in need of improvement or clarification, including potential missing tests for the new features, consistency in logging levels, and ensuring proper logging practices (e.g., logging exceptions at the right level). Overall, the code is a positive step forward but still needs some adjustments to ensure robustness and test coverage.

**Score:** Needs Some Work 🔧

### Comments:

- Comment: src/lgtm/__main__.py:84: Consider adding tests for the `_set_logging_level` function to validate the logging level changes accordingly.

- Comment: src/lgtm/__main__.py:29: The introduction of a `verbose` flag for logging levels is great. Ensure your team knows to use it appropriately throughout the documentation.

- Comment: src/lgtm/__main__.py:54: While logging the review publication process, consider adding a `try-except` block so you can log any issues with publishing.

- Comment: src/lgtm/git_client/gitlab.py:48: The `try-except` blocks in your methods are well done but ensure that you're logging the exception detail to provide better context for errors.

- Comment: src/lgtm/base/exceptions.py:7: You might want to consider adding custom messages during the exception initialization to provide more context when the exception is raised.

- Comment: pyproject.toml:66: Be cautious when ignoring the `TRY400` rule; exposing exceptions through logging can sometimes mask crucial debugging information.
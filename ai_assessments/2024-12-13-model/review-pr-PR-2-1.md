# Review for PR: PR-2

> Sample 1

> Using model: gpt-4o

## Summary

> The code changes focus primarily on adding logging throughout the codebase with various levels of detail (info, debug, error, etc.). A new `LGMTException` class is introduced, which extends `ClickException` to log exceptions at varying levels. Additionally, several exception classes now inherit from `LGMTException`, providing more detailed log messages in exception cases. The code refactor also includes enhancements in the logging setup, particularly in `__main__.py`, where verbosity levels can be set. The schemas and exceptions are being restructured, as evidenced by changes in import paths and the creation of a new schemas file.

Overall, the code introduces numerous improvements in the observability of the application but should be modified to ensure consistency and thoroughness. Suggestions and nitpicks have been pointed out in the inline comments.

Key Areas:
1. **Correctness**: No major logic errors found, but logging practices may need refinement.
2. **Code Quality**: Logging is useful, but consistency and clarity in log messages should be improved. Import restructuring looks appropriate.
3. **Testing**: The logging functionality does appear to be tested, but additional tests should be considered, especially around failure cases and log outputs, ensuring logging does not hinder functionality.

**Score:** Nitpicks 🤓

### Comments:

- Comment: scripts/evaluate_review_quality.py:4: Ensure the potential sensitive information isn't logged at DEBUG level inadvertently.

- Comment: src/lgtm/ai/agent.py:6: Consider initializing the logger once and reusing it through this module to avoid creating multiple handlers.

- Comment: src/lgtm/git_client/gitlab.py:115: Be sure to use appropriate logging levels; WARN might be better suited for scenarios where retry is happening due to a failure.

- Comment: src/lgtm/__main__.py:79: Consider warning users when log level changes occur to avoid confusion if they miss the initial log.
# Review for PR: PR-1

> Sample 2

> Using model: gpt-4o

## Summary

> The code introduces several new features and changes to the image processing functionality. There are some correctness, quality, and testing issues that need to be resolved.

**Correctness**:
- A major issue is the change to the model in the migration files which seem to be wrongly merged. It's important to ensure the schema aligns with the intended design.

**Code quality**:
- There is some room for improvement in the readability and maintainability of code in `BatchStorageProcedure` and handling exceptions for streams.

**Testing**:
- While new tests have been added, considering the scope of changes and added functionalities, ensure all edge cases are covered and models are properly validated.

Overall, the codebase is improving but needs some work to reach required standards.

**Score:** Needs Some Work 🔧

### Comments:

- Comment [Quality] 🟢: src/config/settings.py:6: Consider defaulting the `BULK_CREATE_LIST_SERIALIZER_BATCH_SIZE` to a value that is configurable and check for its presence using `hasattr` or `getattr`.

- Comment [Correctness] 🔴: src/images/migrations/0001_initial.py:28: Removing `blank=True` is a breaking change and would affect how the model validates `image` fields. Make sure this is intended.

- Comment [Quality] 🟡: src/images/services/batches.py:58: Instead of retrying within the save method, you might consider using Django's own transaction management to handle retries for failed transactions.

- Comment [Correctness] 🔴: src/images/services/resources.py:43: Consider handling exceptions for network issues explicitly. Use specific exception classes provided by `httpx`.

- Comment [Testing] 🟢: tests/images/test_resources.py:108: Great job adding tests for exceptions. Remember to test for both positive and negative cases.
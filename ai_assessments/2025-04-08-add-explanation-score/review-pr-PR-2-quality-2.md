# Review for PR: PR-2-quality

> Sample 2

> Using model: gpt-4o


🦉 **lgtm Review**

> **Score:** LGTM 👍

**Summary:**

The PR introduces a new markdown formatting system for review comments and integrates it into various parts of the codebase, especially within the GitlabClient class. The change involves moving from a custom formatting method within classes to using a dedicated MarkDownFormatter class for better separation of concerns and reusability. Here is the feedback and suggestions based on my review: - In several parts of the code, the dependency on a formatter is injected into classes like GitlabClient, which is a good move to support different formatting outputs (Markdown, Terminal). - The removal of the computed_property for formatted_severity and formatted_score in favor of using a constants map and dedicated formatter makes the code more streamlined and decoupled. This modification improves maintainability and is a good decision. - The type literals for CommentCategory, CommentSeverity, and ReviewScore are cleanly refactored as reusable types, which improves code readability and reuse. - Tests are updated to reflect changes to the formatting system and ensure that reviews and comments are formatted correctly. Changes Required: - Double-check if any documentation or comments need updating in response to the change to using formatter classes. Other than that, the tests are thorough, covering resulting behaviors in different scenarios, including handling of errors in posting comments to GitLab. Overall, the changes improve the scalability and modularity of the codebase. Well done!
from click import ClickException


class PullRequestDiffError(ClickException):
    message = "Failed to retrieve the diff of the pull request"

    def __init__(self) -> None:
        super().__init__(self.message)


class PullRequestDiffNotFoundError(ClickException):
    message = "No diff found for this pull request"

    def __init__(self) -> None:
        super().__init__(self.message)


class PublishReviewError(ClickException):
    message = "Failed to publish the review"

    def __init__(self) -> None:
        super().__init__(self.message)


class InvalidGitAuthError(ClickException):
    message = "Invalid Git service authentication token"

    def __init__(self) -> None:
        super().__init__(self.message)

from lgtm.base.exceptions import LGMTException


class PullRequestDiffError(LGMTException):
    message = "Failed to retrieve the diff of the pull request"

    def __init__(self) -> None:
        super().__init__(self.message)


class PullRequestDiffNotFoundError(LGMTException):
    message = "No diff found for this pull request"

    def __init__(self) -> None:
        super().__init__(self.message)


class PublishReviewError(LGMTException):
    message = "Failed to publish the review"

    def __init__(self) -> None:
        super().__init__(self.message)


class InvalidGitAuthError(LGMTException):
    message = "Invalid Git service authentication token"

    def __init__(self) -> None:
        super().__init__(self.message)

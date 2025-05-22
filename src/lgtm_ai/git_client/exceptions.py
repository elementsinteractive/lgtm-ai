from lgtm_ai.base.exceptions import LGTMException


class PullRequestDiffError(LGTMException):
    message = "Failed to retrieve the diff of the pull request"

    def __init__(self) -> None:
        super().__init__(self.message)


class PullRequestMetadataError(LGTMException):
    message = "Failed to retrieve the metadata of the pull request"

    def __init__(self) -> None:
        super().__init__(self.message)


class PullRequestDiffNotFoundError(LGTMException):
    message = "No diff found for this pull request"

    def __init__(self) -> None:
        super().__init__(self.message)


class PublishReviewError(LGTMException):
    message = "Failed to publish the review"

    def __init__(self) -> None:
        super().__init__(self.message)


class PublishGuideError(LGTMException):
    message = "Failed to publish the review guide"

    def __init__(self) -> None:
        super().__init__(self.message)


class InvalidGitAuthError(LGTMException):
    message = "Invalid Git service authentication token"

    def __init__(self) -> None:
        super().__init__(self.message)


class DecodingFileError(LGTMException):
    message = "Failed to decode the file"

    def __init__(self) -> None:
        super().__init__(self.message)

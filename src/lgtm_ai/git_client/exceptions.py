from lgtm_ai.base.exceptions import LGTMException


class PullRequestDiffError(LGTMException):
    _message = "Failed to retrieve the diff of the pull request"

    def __init__(self) -> None:
        super().__init__(self._message)


class PullRequestMetadataError(LGTMException):
    _message = "Failed to retrieve the metadata of the pull request"

    def __init__(self) -> None:
        super().__init__(self._message)


class PullRequestDiffNotFoundError(LGTMException):
    _message = "No diff found for this pull request"

    def __init__(self) -> None:
        super().__init__(self._message)


class PublishReviewError(LGTMException):
    _message = "Failed to publish the review"

    def __init__(self) -> None:
        super().__init__(self._message)


class PublishGuideError(LGTMException):
    _message = "Failed to publish the review guide"

    def __init__(self) -> None:
        super().__init__(self._message)


class InvalidGitAuthError(LGTMException):
    _message = "Invalid Git service authentication token"

    def __init__(self) -> None:
        super().__init__(self._message)


class DecodingFileError(LGTMException):
    _message = "Failed to decode the file"

    def __init__(self) -> None:
        super().__init__(self._message)

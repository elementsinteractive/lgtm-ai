from click import ClickException


class PullRequestDiffError(ClickException):
    message = "Failed to retrieve the diff of the pull request"

    def __init__(self) -> None:
        super().__init__(self.message)


class InvalidGitAuthError(ClickException):
    message = "Invalid Git service authentication token"

    def __init__(self) -> None:
        super().__init__(self.message)

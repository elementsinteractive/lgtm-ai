from click import ClickException


class ProjectNotFoundError(ClickException):
    message = "Cannot find the specified project"

    def __init__(self) -> None:
        super().__init__(self.message)


class PullRequestNotFoundError(ClickException):
    message = "Cannot find the specified pull request"

    def __init__(self) -> None:
        super().__init__(self.message)


class DiffsCollectionError(ClickException):
    message = "Cannot collect diffs from the specified pull request"

    def __init__(self) -> None:
        super().__init__(self.message)


class InvalidGitAuthError(ClickException):
    message = "Invalid Git service authentication token"

    def __init__(self) -> None:
        super().__init__(self.message)

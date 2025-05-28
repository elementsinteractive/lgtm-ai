import logging
from typing import IO, Any

from click import ClickException

logger = logging.getLogger("lgtm")


class LGTMException(ClickException):
    def show(self, file: IO[Any] | None = None) -> None:
        """LGTM exceptions expose the traceback in debug mode."""
        logger.debug(self.format_message(), exc_info=True)
        logger.error(self.format_message(), exc_info=False)


class NothingToReviewError(LGTMException):
    def __init__(self, exclude: tuple[str, ...] | None = None) -> None:
        exclude = exclude or ()
        super().__init__(f"Nothing to review after excluding file patterns {', '.join(exclude)}.")

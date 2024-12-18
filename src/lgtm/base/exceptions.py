import logging
from typing import IO, Any

from click import ClickException

logger = logging.getLogger("lgtm")


class LGMTException(ClickException):
    def show(self, file: IO[Any] | None = None) -> None:
        """LGTM exceptions expose the traceback in debug mode."""
        logger.debug(self.format_message(), exc_info=True)
        logger.error(self.format_message(), exc_info=False)

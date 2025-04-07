from typing import Final

from lgtm.ai.schemas import CommentSeverity, ReviewScore

SEVERITY_MAP: Final[dict[CommentSeverity, str]] = {
    "LOW": "🔵",
    "MEDIUM": "🟡",
    "HIGH": "🔴",
}

SCORE_MAP: Final[dict[ReviewScore, str]] = {
    "LGTM": "👍",
    "Nitpicks": "🤓",
    "Needs Some Work": "🔧",
    "Needs a Lot of Work": "🚨",
    "Abandon": "❌",
}

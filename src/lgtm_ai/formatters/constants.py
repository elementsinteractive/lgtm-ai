from typing import Final

from lgtm_ai.ai.schemas import CommentCategory, CommentSeverity, ReviewScore

SEVERITY_MAP: Final[dict[CommentSeverity, str]] = {
    "LOW": "🔵",
    "MEDIUM": "🟡",
    "HIGH": "🔴",
}

SCORE_MAP: Final[dict[ReviewScore, str]] = {
    "LGTM": "👍",
    "Nitpicks": "🤓",
    "Needs Work": "🔧",
    "Needs a Lot of Work": "🚨",
    "Abandon": "❌",
}

CATEGORY_MAP: Final[dict[CommentCategory, str]] = {
    "Correctness": "✅",
    "Quality": "✨",
    "Testing": "🧪",
    "Security": "🔒",
}

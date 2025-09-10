from lgtm_ai.ai.schemas import SupportedAIModels

DEFAULT_AI_MODEL: SupportedAIModels = "gemini-2.0-flash"
DEFAULT_INPUT_TOKEN_LIMIT = 500000
DEFAULT_ISSUE_REGEX = r"(?:refs?|closes?|resolves?)[:\s]*((?:#\d+)|(?:#?[A-Z]+-\d+))|(?:fix|feat|docs|style|refactor|perf|test|build|ci)\((?:#(\d+)|#?([A-Z]+-\d+))\)!?:"

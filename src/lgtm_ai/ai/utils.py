from typing import cast

from lgtm_ai.ai.exceptions import InvalidGeminiWildcard, InvalidModelWildCard
from lgtm_ai.ai.schemas import SupportedGeminiModel


def match_model_by_wildcard[T](model_name: str, model_list: tuple[T, ...]) -> list[T] | None:
    """Match a model name against a list of models with wildcard support."""
    if model_name in model_list:
        return [cast(T, model_name)]

    if model_name.count("*") > 1 or ("*" in model_name and not model_name.endswith("*")):
        raise InvalidModelWildCard(model_name)

    if not model_name.endswith("*"):
        return None

    all_matches = [model for model in model_list if str(model).startswith(model_name.replace("*", ""))]
    if not all_matches:
        return None

    return all_matches


def select_latest_gemini_model(matches: list[SupportedGeminiModel]) -> SupportedGeminiModel:
    if len(matches) == 1:
        return matches[0]

    # If one of them is not a `preview` or `exp` model, select it
    # This is because out of several possible models given a wildcard, we assume preference for stable models.
    # If the user wanted a preview or experimental model, they could have specified it in the wildcard itself:
    # e.g.: `gemini-2.5-flash*` will select the latest stable, while `gemini-2.5-flash-p*` will select the latest preview.
    non_preview_matches = [model for model in matches if all(word not in model for word in ("preview", "exp"))]
    if non_preview_matches:
        if len(non_preview_matches) > 1:
            raise InvalidGeminiWildcard(matches)
        return non_preview_matches[0]

    model_to_date = {model: model.split("-")[-2:] for model in matches}

    def _looks_like_date(date: list[str]) -> bool:
        return len(date) == 2 and all(elem.isdigit() for elem in date)

    if not all(_looks_like_date(date) for date in model_to_date.values()):
        raise InvalidGeminiWildcard(matches)

    # Get the latest model by date
    latest_model = max(
        matches,
        key=lambda model: tuple(int(x) for x in model_to_date[model]),
    )
    return latest_model

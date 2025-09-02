import re


def validate_regex(value: str | None) -> str | None:
    if value is None:
        return value

    try:
        re.compile(value)
    except re.error as err:
        raise ValueError(f"Invalid regex: {err}") from err
    else:
        return value

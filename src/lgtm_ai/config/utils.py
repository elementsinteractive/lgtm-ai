from collections.abc import Sequence
from typing import Annotated

from pydantic import AfterValidator


def _unique_with_order[T](seq: Sequence[T]) -> tuple[T, ...]:
    """Return a list of unique elements while preserving the order."""
    seen = set()
    saved = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            saved.append(x)
    return tuple(saved)


type Unique[T] = Annotated[tuple[T, ...], AfterValidator(_unique_with_order)]

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
"""Deduplicated tuple of type T, preserving order."""

type TupleOrNone[T] = Annotated[tuple[T, ...] | None, AfterValidator(lambda v: v if v else None)]
"""Tuple of type T or None if empty. In click, CLI args that are tuples and are not given are just empty tuples.

To signify that the arg was not given, we transform it to `None`."""

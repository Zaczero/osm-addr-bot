from dataclasses import dataclass, field
from typing import Any, Callable

from aliases import Identifier, Tags


@dataclass(frozen=True, kw_only=True, slots=True)
class Check:
    identifier: Identifier
    priority: int
    critical: bool
    desc: str
    extra: str | None
    docs: str | None
    pre_fn: Callable[[Tags], bool]
    post_fn: Callable[[Any, list], list] | None = None
    edit_tags: tuple[str, ...] = tuple()

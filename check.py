from dataclasses import dataclass
from typing import Callable, Any, Optional

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
    post_fn: Optional[Callable[[Any, list], list]] = None

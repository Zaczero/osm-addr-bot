from dataclasses import dataclass
from typing import Callable, Any, Optional


@dataclass(frozen=True, kw_only=True, slots=True)
class Check:
    priority: int
    message: str
    message_fix: str
    overpass: str
    post_fn: Optional[Callable[[Any, list], list]] = None

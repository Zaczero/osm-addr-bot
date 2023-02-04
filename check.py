from dataclasses import dataclass
from typing import Callable, Any, Optional


@dataclass(frozen=True, kw_only=True, slots=True)
class Check:
    identifier: str
    priority: int
    message: str
    message_fix: str
    pre_fn: Callable[[dict[str, str]], bool]
    post_fn: Optional[Callable[[Any, list], list]] = None

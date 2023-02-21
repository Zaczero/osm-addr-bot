from dataclasses import dataclass
from typing import Any, Callable

from aliases import Identifier, Tags
from check_base import CheckBase


@dataclass(frozen=True, kw_only=True, slots=True)
class Check(CheckBase):
    priority: int
    critical: bool
    desc: str
    extra: str | None
    docs: str | None

    pre_fn: Callable[[Tags], bool] | None = None
    post_fn: Callable[[Any, list], list] | None = None

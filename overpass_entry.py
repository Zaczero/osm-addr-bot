from dataclasses import dataclass

from checks import Check
from utils import parse_timestamp


@dataclass(slots=True, kw_only=True)
class OverpassEntry:
    timestamp: int
    changeset_id: int
    element_type: str
    element_id: int
    tags: dict
    reason: Check

    # noinspection PyTypeChecker
    def __post_init__(self):
        self.timestamp = parse_timestamp(self.timestamp)
        self.changeset_id = int(self.changeset_id)
        self.element_id = int(self.element_id)

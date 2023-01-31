from dataclasses import dataclass

from checks import Check


@dataclass(slots=True)
class OverpassEntry:
    changeset_id: int
    element_type: str
    element_id: int
    reason: Check

    def __post_init__(self):
        self.changeset_id = int(self.changeset_id)
        self.element_id = int(self.element_id)

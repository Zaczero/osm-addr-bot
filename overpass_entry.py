from dataclasses import dataclass

from geopy import Point

from aliases import ElementType, Tags

UID_OFFSET = 1 << 27


@dataclass(slots=True, kw_only=True)
class OverpassEntry:
    timestamp: int
    changeset_id: int
    element_type: ElementType
    element_id: int
    tags: Tags
    nodes: list[int]

    bb_min: Point
    bb_max: Point
    bb_size: tuple[float, float]

    uid: int = 0

    # noinspection PyTypeChecker
    def __post_init__(self):
        from utils import parse_timestamp

        if isinstance(self.timestamp, str):
            self.timestamp = parse_timestamp(self.timestamp)

        self.changeset_id = int(self.changeset_id)
        self.element_id = int(self.element_id)

        if self.element_type == 'node':
            self.uid = -self.element_id
        elif self.element_type == 'way':
            self.uid = self.element_id + UID_OFFSET
        else:  # relation
            assert self.element_id < UID_OFFSET, 'Increase uid offset'
            self.uid = self.element_id

    def __hash__(self):
        return self.uid

    def __eq__(self, other):
        if isinstance(other, OverpassEntry):
            return self.uid == other.uid

        return NotImplemented

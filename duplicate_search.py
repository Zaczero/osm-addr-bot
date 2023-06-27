from aliases import Tags
from overpass_entry import OverpassEntry

WHITELIST_TAGS = (
    'addr:',
    'building',
    'capacity',
    'check_date',
    'construction',
    'fixme',
    'height',
    'layer',
    'name',
    'note',
    'proposed',
    'roof',
    'source',
    'start_date'
)

EQUAL_TAGS = (
    'addr:city',
    'addr:housenumber',
    'addr:place',
    'addr:street',
    'addr:unit'
)


def check_whitelist(tags: Tags) -> bool:
    return all(
        any(
            t.startswith(w)
            for w in WHITELIST_TAGS
        )
        for t in tags
    )


def check_equal_tag(left: Tags, right: Tags, key: str) -> bool:
    return left.get(key, None) == right.get(key, None)


def check_equal_tags(left: OverpassEntry, right: OverpassEntry) -> bool:
    return all(check_equal_tag(left.tags, right.tags, t) for t in EQUAL_TAGS)


def duplicate_search(entry: OverpassEntry, ref: list[OverpassEntry]) -> list[OverpassEntry]:
    assert 'addr:housenumber' in entry.tags

    return [
        e for e in ref
        if e != entry
        and check_whitelist(e.tags)
        and check_equal_tags(e, entry)
    ]

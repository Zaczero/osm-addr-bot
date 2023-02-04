import re

from check import Check
from utils import normalize

POSTCODE_RE = re.compile(r'^\d{2}-\d{3}([;,]\d{2}-\d{3})*$')

# noinspection SpellCheckingInspection
ALL_CHECKS = [
    # TODO: more mistype checks
    # TODO: batched post_fn for all changesets
    # TODO: simplify checks identifier system

    Check(
        identifier='BAD_CITY_WITH_PLACE',
        priority=50,

        message="Wartość addr:city jest niezgodna z addr:place.",
        message_fix="Jeśli adres ma nazwę ulicy, usuń addr:place i zastosuj kombinację addr:city + addr:street. "
                    "Jeśli nie, pozostaw tylko addr:place.",
        pre_fn=lambda t: ('addr:city' in t) and ('addr:place' in t) and (t['addr:city'] != t['addr:place']),
        post_fn=lambda o, i: o.query_place_not_in_area(i)
    ),

    Check(
        identifier='BAD_POSTCODE_FORMAT',
        priority=100,

        message="Nieprawidłowa wartość addr:postcode.",
        message_fix="Kod pocztowy powinien być formatu XX-XXX, gdzie X oznacza cyfrę.",
        pre_fn=lambda t: ('addr:postcode' in t) and (not POSTCODE_RE.match(t['addr:postcode']))
    ),

    Check(
        identifier='CITY_WITH_PLACE_MISTYPE',
        priority=85,

        message="Wartość addr:city lub addr:place zawiera błąd w pisowni.",
        message_fix="Upewnij się, czy wielkość liter jest poprawna, oraz czy nigdzie nie ma dodatkowych znaków.",
        pre_fn=lambda t: ('addr:city' in t) and ('addr:place' in t) and (t['addr:city'] != t['addr:place']) and
                         (normalize(t['addr:city']) == normalize(t['addr:place'])),
    ),

    Check(
        identifier='DUPLICATED',
        priority=0,

        message="Duplikat adresu w okolicy.",
        message_fix="Adres można oznaczyć na dwa sposoby: na obszarze (dokładniejsze) albo na punkcie. "
                    "Aktualizując adres, należy się upewnić, czy w okolicy nie pozostały żadne duplikaty.",
        pre_fn=lambda t: ('addr:housenumber' in t),
        post_fn=lambda o, i: o.query_duplicates(i)
    ),

    Check(
        identifier='NUMBER_WITHOUT_CITY',
        priority=30,

        message="Adres jest niekompletny, brakuje informacji o miejscowości.",
        message_fix="Jeśli adres ma nazwę ulicy, zastosuj kombinację addr:city + addr:street. "
                    "Jeśli nie, przekaż nazwę miejscowości w addr:place.",
        pre_fn=lambda t: ('addr:housenumber' in t) and ('addr:city' not in t) and ('addr:place' not in t)
    ),

    Check(
        identifier='NUMBER_WITHOUT_STREET',
        priority=30,

        message="Adres jest niekompletny, brakuje informacji o nazwie ulicy.",
        message_fix="Jeśli adres ma nazwę ulicy, dodaj ją w addr:street. "
                    "Jeśli nie, zamień addr:city na addr:place - tak oznaczamy adresy bez ulic.",
        pre_fn=lambda t: ('addr:housenumber' in t) and ('addr:city' in t) and
                         ('addr:place' not in t) and ('addr:street' not in t)
    ),

    Check(
        identifier='PLACE_MISTYPE',
        priority=80,

        message="Wartość addr:place zawiera błąd w pisowni.",
        message_fix="Upewnij się, czy wielkość liter jest poprawna, oraz czy nigdzie nie ma dodatkowych znaków.",
        pre_fn=lambda t: ('addr:place' in t),
        post_fn=lambda o, i: o.query_place_mistype(i)
    ),

    Check(
        identifier='PLACE_WITH_STREET',
        priority=100,

        message="Klucz addr:place oznacza brak nazwy ulicy. "
                "Kombinacja z addr:street (który definiuje nazwę ulicy) jest błędna.",
        message_fix="Jeśli adres ma nazwę ulicy, zamień addr:place na addr:city. "
                    "Jeśli nie, usuń addr:street.",
        pre_fn=lambda t: ('addr:place' in t) and ('addr:street' in t)
    ),

    Check(
        identifier='UNKNOWN_STREET_NAME',
        priority=10,

        message="Nazwa ulicy nie istnieje w okolicy.",
        message_fix="Jeśli adres ma nazwę ulicy, upewnij się, że jest ona poprawna. "
                    "Jeśli nie, usuń addr:street, a nazwę miejscowości przekaż w addr:place.",
        pre_fn=lambda t: ('addr:street' in t),
        post_fn=lambda o, i: o.query_street_names(i)
    ),

]

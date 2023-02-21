import re
from itertools import chain

from category import Category
from check import Check
from utils import normalize

# TODO: more mistype checks

POSTCODE_RE = re.compile(r'^\d{2}-\d{3}([;,]\d{2}-\d{3})*$')

OVERPASS_CATEGORIES = [
    Category(
        identifier='ADDRESS',

        header_critical='Zauważyłem, że Twoja zmiana zawiera niepoprawne adresy. '
                        'Przygotowałem listę obiektów do poprawy oraz dodatkowe informacje:',

        header='Zauważyłem, że Twoja zmiana zawiera adresy wymagające dodatkowej uwagi. '
               'Przygotowałem listę obiektów oraz dodatkowe informacje:',

        docs='Dokumentacja adresów (po polsku):\n'
             'https://wiki.openstreetmap.org/wiki/Pl:Key:addr:*',

        pre_fn=lambda t: any(key.startswith('addr:') for key in t),
        edit_tags=('addr:*', ),

        checks=[
            Check(
                identifier='BAD_CITY_WITH_PLACE',
                priority=50,

                critical=True,
                desc="Wartość addr:city jest niezgodna z addr:place.",
                extra="Jeśli adres ma nazwę ulicy, usuń addr:place i zastosuj kombinację addr:city + addr:street. "
                      "Jeśli nie, pozostaw tylko addr:place.",

                docs=None,

                pre_fn=lambda t: ('addr:city' in t) and ('addr:place' in t) and (t['addr:city'] != t['addr:place']),
                post_fn=lambda o, i: o.query_place_not_in_area(i)
            ),

            Check(
                identifier='BAD_POSTCODE_FORMAT',
                priority=100,

                critical=True,
                desc="Nieprawidłowa wartość addr:postcode.",
                extra="Kod pocztowy powinien być formatu XX-XXX, gdzie X oznacza cyfrę.",

                docs=None,

                pre_fn=lambda t: ('addr:postcode' in t) and (not POSTCODE_RE.match(t['addr:postcode']))
            ),

            Check(
                identifier='CITY_WITH_PLACE_MISTYPE',
                priority=85,

                critical=True,
                desc="Wartość addr:city lub addr:place zawiera błąd w pisowni.",
                extra="Upewnij się, czy wielkość liter jest poprawna, oraz czy nigdzie nie ma dodatkowych znaków.",

                docs=None,

                pre_fn=lambda t: ('addr:city' in t) and ('addr:place' in t) and (t['addr:city'] != t['addr:place']) and
                                 (normalize(t['addr:city']) == normalize(t['addr:place'])),
            ),

            Check(
                identifier='DUPLICATED',
                priority=0,

                critical=True,
                desc="Duplikat adresu w okolicy.",
                extra="Adres można oznaczyć na dwa sposoby: na obszarze (dokładniejsze) albo na punkcie. "
                      "Aktualizując adres, należy się upewnić, czy w okolicy nie pozostały żadne duplikaty.",

                docs=None,

                pre_fn=lambda t: ('addr:housenumber' in t),
                post_fn=lambda o, i: o.query_duplicates(i)
            ),

            Check(
                identifier='NUMBER_WITHOUT_CITY',
                priority=30,

                critical=True,
                desc="Adres jest niekompletny, brakuje informacji o miejscowości.",
                extra="Jeśli adres ma nazwę ulicy, zastosuj kombinację addr:city + addr:street. "
                      "Jeśli nie, przekaż nazwę miejscowości w addr:place.",

                docs=None,

                pre_fn=lambda t: ('addr:housenumber' in t) and ('addr:city' not in t) and ('addr:place' not in t)
            ),

            Check(
                identifier='NUMBER_WITHOUT_STREET',
                priority=30,

                critical=True,
                desc="Adres jest niekompletny, brakuje informacji o nazwie ulicy.",
                extra="Jeśli adres ma nazwę ulicy, dodaj ją w addr:street. "
                      "Jeśli nie, zamień addr:city na addr:place - tak oznaczamy adresy bez ulic.",

                docs=None,

                pre_fn=lambda t: ('addr:housenumber' in t) and ('addr:city' in t) and
                                 ('addr:place' not in t) and ('addr:street' not in t)
            ),

            Check(
                identifier='PLACE_MISTYPE',
                priority=80,

                critical=True,
                desc="Wartość addr:place zawiera błąd w pisowni.",
                extra="Upewnij się, czy wielkość liter jest poprawna, oraz czy nigdzie nie ma dodatkowych znaków.",

                docs=None,

                pre_fn=lambda t: ('addr:place' in t),
                post_fn=lambda o, i: o.query_place_mistype(i)
            ),

            Check(
                identifier='PLACE_WITH_STREET',
                priority=100,

                critical=True,
                desc="Klucz addr:place oznacza brak nazwy ulicy. "
                     "Kombinacja z addr:street (który definiuje nazwę ulicy) jest błędna.",
                extra="Jeśli adres ma nazwę ulicy, zamień addr:place na addr:city. "
                      "Jeśli nie, usuń addr:street.",

                docs=None,

                pre_fn=lambda t: ('addr:place' in t) and ('addr:street' in t)
            ),

            Check(
                identifier='UNKNOWN_STREET_NAME',
                priority=10,

                critical=False,
                desc="Nazwa ulicy nie istnieje w okolicy.",
                extra="Jeśli adres ma nazwę ulicy, upewnij się, że jest ona poprawna. "
                      "Jeśli nie, usuń addr:street, a nazwę miejscowości przekaż w addr:place.",

                docs=None,

                pre_fn=lambda t: ('addr:street' in t),
                post_fn=lambda o, i: o.query_street_names(i)
            ),
        ]
    ),
]

CHANGESET_CATEGORIES = [

]

ALL_CATEGORIES = list(chain(
    OVERPASS_CATEGORIES,
    CHANGESET_CATEGORIES
))

ALL_CHECKS = list(chain.from_iterable(c.checks for c in ALL_CATEGORIES))

ALL_IDS = [c.identifier for c in ALL_CATEGORIES] + [c.identifier for c in ALL_CHECKS]

assert len(set(ALL_IDS)) == len(ALL_IDS), 'Identifiers must be unique'

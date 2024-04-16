import re
from itertools import chain

from category import Category
from check import Check
from utils import normalize

# TODO: more mistype checks

POSTCODE_RE = re.compile(r'^\d{2}-\d{3}([;,]\d{2}-\d{3})*$')
WEBSITE_PROTOCOL_RE = re.compile(r'^\w{2,}://')
WEBSITE_DUPLICATED_PROTOCOL_RE = re.compile(r'^\w{2,}://\w{2,}://')
WEBSITE_SHORTENER_RE = re.compile(r'^\w{2,}://(www\.)?(tinyurl\.com|tiny\.(cc|pl)|(bit|cutt)\.ly|[gt]\.co|goo\.gl(?!/maps))/',
                                  re.IGNORECASE)

OVERPASS_CATEGORIES: tuple[Category, ...] = (
    Category(
        identifier='ADDRESS',
        min_changesets=0,

        header_critical='Zauważyłem, że Twoja zmiana zawiera niepoprawne adresy. '
                        'Przygotowałem listę obiektów do poprawy oraz dodatkowe informacje:',

        header='Zauważyłem, że Twoja zmiana zawiera adresy wymagające dodatkowej uwagi. '
               'Przygotowałem listę obiektów oraz dodatkowe informacje:',

        docs='Dokumentacja adresów (po polsku):\n'
             'https://wiki.openstreetmap.org/wiki/Pl:Key:addr:*',

        selectors=('addr:*',),

        checks=(
            Check(
                identifier='BAD_CITY_WITH_PLACE',
                priority=50,

                critical=True,
                desc="Podana kombinacja addr:city + addr:place jest nieprawidłowa.",
                extra="Jeśli adres ma nazwę ulicy, usuń addr:place i zastosuj kombinację addr:city + addr:street. "
                      "Jeśli nie, pozostaw tylko addr:place.",

                docs=None,

                selectors=('addr:city', 'addr:place'),
                pre_fn=lambda t: (t['addr:city'] != t['addr:place']),
                post_fn=lambda o, i: o.query_place_not_in_area(i)
            ),

            Check(
                identifier='BAD_POSTCODE_FORMAT',
                priority=100,

                critical=True,
                desc="Nieprawidłowa wartość addr:postcode.",
                extra="Kod pocztowy powinien być formatu XX-XXX, gdzie X oznacza cyfrę.",

                docs=None,

                selectors=('addr:postcode',),
                pre_fn=lambda t: (not POSTCODE_RE.match(t['addr:postcode']))
            ),

            Check(
                identifier='CITY_WITH_PLACE_MISTYPE',
                priority=85,

                critical=True,
                desc="Wartość addr:city lub addr:place zawiera błąd w pisowni.",
                extra="Upewnij się, czy wielkość liter jest poprawna, oraz czy nigdzie nie ma dodatkowych znaków.",

                docs=None,

                selectors=('addr:city', 'addr:place'),
                pre_fn=lambda t: (t['addr:city'] != t['addr:place']) and
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

                selectors=('addr:housenumber',),
                post_fn=lambda o, i: o.query_duplicates(i)
            ),

            # Check(
            #     identifier='NUMBER_WITHOUT_CITY',
            #     priority=30,

            #     critical=True,
            #     desc="Adres jest niekompletny, brakuje informacji o miejscowości.",
            #     extra="Jeśli adres ma nazwę ulicy, zastosuj kombinację addr:city + addr:street. "
            #           "Jeśli nie, przekaż nazwę miejscowości w addr:place.",

            #     docs=None,

            #     selectors=('addr:housenumber',),
            #     pre_fn=lambda t: ('addr:city' not in t) and ('addr:place' not in t)
            # ),

            Check(
                identifier='NUMBER_WITHOUT_STREET',
                priority=30,

                critical=True,
                desc="Adres jest niekompletny, brakuje informacji o nazwie ulicy.",
                extra="Jeśli adres ma nazwę ulicy, dodaj ją w addr:street. "
                      "Jeśli nie, zamień addr:city na addr:place - tak oznaczamy adresy bez ulic.",

                docs=None,

                selectors=('addr:housenumber', 'addr:city'),
                pre_fn=lambda t: ('addr:place' not in t) and ('addr:street' not in t)
            ),

            Check(
                identifier='PLACE_MISTYPE',
                priority=80,

                critical=True,
                desc="Wartość addr:place zawiera błąd w pisowni.",
                extra="Upewnij się, czy wielkość liter jest poprawna, oraz czy nigdzie nie ma dodatkowych znaków.",

                docs=None,

                selectors=('addr:place',),
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

                selectors=('addr:place', 'addr:street'),
            ),

            Check(
                identifier='UNKNOWN_STREET_NAME',
                priority=10,

                critical=False,
                desc="Nazwa ulicy nie istnieje w okolicy.",
                extra="Jeśli adres ma nazwę ulicy, upewnij się, że jest ona poprawna. "
                      "Jeśli nie, usuń addr:street, a nazwę miejscowości przekaż w addr:place.",

                docs=None,

                selectors=('addr:street',),
                post_fn=lambda o, i: o.query_street_names(i)
            ),
        )
    ),

    Category(
        identifier='REDUNDANCY',
        min_changesets=0,

        header_critical='Zauważyłem, że Twoja zmiana zawiera nadmiarowe informacje. '
                        'Przygotowałem listę obiektów do poprawy oraz dodatkowe informacje:',

        header='Zauważyłem, że Twoja zmiana zawiera nadmiarowe informacje. '
               'Przygotowałem listę obiektów oraz dodatkowe informacje:',

        docs=None,

        checks=(
            Check(
                identifier='PARCEL_LOCKER_WITH_NAME',

                critical=True,
                desc="Paczkomat nie powinien mieć nazwy.",
                extra="Nazwa nadawana jest automatycznie, na podstawie wartości brand. "
                      "Opcjonalnie, numer identyfikacyjny może być przekazany w polu ref.",

                docs='Dokumentacja paczkomatów (po polsku):\n'
                     'https://wiki.openstreetmap.org/wiki/Pl:Tag:amenity%3Dparcel_locker',

                selectors=('brand:wikidata', 'name'),
                pre_fn=lambda t: t['brand:wikidata'] in {
                    'Q110738715',  # Allegro One Box
                    'Q110970254',  # Paczkomat InPost
                    'Q114273730',  # DPD Pickup Station
                    'Q110457879',  # Orlen Paczka
                },
            ),
        )
    ),

    Category(
        identifier='SYNTAX',
        min_changesets=0,

        header_critical='Zauważyłem, że Twoja zmiana zawiera niepoprawną składnię. '
                        'Przygotowałem listę obiektów do poprawy oraz dodatkowe informacje:',

        header='Zauważyłem, że Twoja zmiana zawiera niepoprawną składnię. '
               'Przygotowałem listę obiektów oraz dodatkowe informacje:',

        docs=None,

        checks=(
            # Check(
            #     identifier='WEBSITE_WITHOUT_PROTOCOL',

            #     critical=True,
            #     desc='W adresie strony internetowej brakuje protokołu.',
            #     extra='Poprawny adres zaczyna się najczęściej od https:// lub http://.',

            #     docs='Dokumentacja adresów WWW (po polsku):\n'
            #          'https://wiki.openstreetmap.org/wiki/Pl%3AKey%3Awebsite',

            #     partial_selectors=True,
            #     selectors=('url', 'website', 'contact:website'),
            #     pre_fn=lambda t: \
            #     ('url' in t and not WEBSITE_PROTOCOL_RE.match(t['url'])) or \
            #     ('website' in t and not WEBSITE_PROTOCOL_RE.match(t['website'])) or \
            #     ('contact:website' in t and not WEBSITE_PROTOCOL_RE.match(t['contact:website']))
            # ),

            Check(
                identifier='WEBSITE_WITH_REPEATED_PROTOCOL',

                critical=True,
                desc='Adres strony internetowej zawiera powtórzone protokoły.',
                extra='Poprawny adres nie może zawierać więcej niż jednego protokołu, jak np. https://https://.',

                docs='Dokumentacja adresów WWW (po polsku):\n'
                     'https://wiki.openstreetmap.org/wiki/Pl%3AKey%3Awebsite',

                partial_selectors=True,
                selectors=('url', 'website', 'contact:website'),
                pre_fn=lambda t: \
                ('url' in t and WEBSITE_DUPLICATED_PROTOCOL_RE.match(t['url'])) or \
                ('website' in t and WEBSITE_DUPLICATED_PROTOCOL_RE.match(t['website'])) or \
                ('contact:website' in t and WEBSITE_DUPLICATED_PROTOCOL_RE.match(t['contact:website']))
            ),

            Check(
                identifier='WEBSITE_URL_SHORTENER',

                critical=True,
                desc='Adres strony internetowej został skrócony przez serwis typu URL shortener.',
                extra='Przekazując adres strony, upewnij się, że jest on w pełnej, bezpośredniej formie.',

                docs=None,

                partial_selectors=True,
                selectors=('url', 'website', 'contact:website'),
                pre_fn=lambda t: \
                ('url' in t and WEBSITE_SHORTENER_RE.match(t['url'])) or \
                ('website' in t and WEBSITE_SHORTENER_RE.match(t['website'])) or \
                ('contact:website' in t and WEBSITE_SHORTENER_RE.match(t['contact:website']))
            ),
        ),
    ),

    Category(
        identifier='TAGS_COMBINATION',
        min_changesets=10,

        header_critical='Zauważyłem, że Twoja zmiana zawiera niepoprawne połączenie tagów. '
                        'Przygotowałem listę obiektów do poprawy oraz dodatkowe informacje:',

        header='Zauważyłem, że Twoja zmiana zawiera niepoprawne połączenie tagów. '
               'Przygotowałem listę obiektów oraz dodatkowe informacje:',

        docs=None,

        checks=(
            Check(
                identifier='CONSTRUCTION_NOT_REMOVED',

                critical=False,
                desc='Klucz construction=* nie został usunięty.',
                extra='Jeżeli budowa została zakończona należy usunąć dotychczasowe tagowanie wskazujące na budowę.',

                docs=None,

                selectors=('construction'),
                pre_fn=lambda t: \
                t['construction'] in (
                    t.get('building'),
                    t.get('landuse'),
                    t.get('highway'),
                    t.get('railway')
                )
            )
        )
    )
)

CHANGESET_CATEGORIES: tuple[Category, ...] = tuple()

ALL_CATEGORIES = OVERPASS_CATEGORIES + CHANGESET_CATEGORIES
ALL_CHECKS = tuple(chain.from_iterable(c.checks for c in ALL_CATEGORIES))
ALL_IDS = tuple(c.identifier for c in chain(ALL_CATEGORIES, ALL_CHECKS))

assert len(set(ALL_IDS)) == len(ALL_IDS), 'Identifiers must be unique'

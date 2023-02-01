from check import Check

# noinspection SpellCheckingInspection
ALL_CHECKS = [

    # BAD_CITY_WITH_PLACE
    # Check(
    #     message="Wartość addr:city jest niezgodna z addr:place.",
    #     message_fix="Jeśli adres ma nazwę ulicy, usuń addr:place i zastosuj kombinację addr:city + addr:street. "
    #                 "W przeciwnym razie, pozostaw tylko addr:place.",
    #     overpass="['addr:city']['addr:place'](if: t['addr:city'] != t['addr:place'])",
    # ),
    # TODO: validate is_in: https://www.openstreetmap.org/way/54562549

    # DUPLICATED
    Check(
        message="Duplikat adresu w okolicy.",
        message_fix="Adres można oznaczyć na dwa sposoby: na obszarze (dokładniejsze) albo na punkcie. "
                    "Aktualizując adres, należy się upewnić, czy w okolicy nie pozostały żadne duplikaty.",
        overpass="['addr:housenumber']",
        post_fn=lambda o, i: o.query_duplicates(i)
    ),

    # NUMBER_WITHOUT_CITY
    Check(
        message="Adres jest niekompletny, brakuje informacji o miejscowości.",
        message_fix="Jeśli adres ma nazwę ulicy, zastosuj kombinację addr:city + addr:street. "
                    "W przeciwnym razie, przekaż nazwę w addr:place.",
        overpass="['addr:housenumber'][!'addr:city'][!'addr:place']"
    ),

    # PLACE_WITH_STREET
    Check(
        message="Klucz addr:place oznacza brak nazwy ulicy. "
                "Kombinacja z addr:street (który definiuje nazwę ulicy) jest błędna.",
        message_fix="Jeśli adres ma nazwę ulicy, zamień addr:place na addr:city. "
                    "W przeciwnym razie, usuń addr:street.",
        overpass="['addr:place']['addr:street']"
    ),

]

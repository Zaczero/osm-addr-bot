from check import Check

# noinspection SpellCheckingInspection
ALL_CHECKS = [

    # BAD_CITY_WITH_PLACE
    Check(
        message="Wartość addr:city jest niezgodna z addr:place.",
        message_fix="Jeśli adres ma nazwę ulicy, usuń addr:place i zastosuj kombinację addr:city + addr:street. "
                    "Jeśli nie, pozostaw tylko addr:place.",
        overpass="['addr:city']['addr:place'](if: t['addr:city'] != t['addr:place'])",
        post_fn=lambda o, i: o.query_place_not_in_area(i)
    ),

    # BAD_POSTCODE
    Check(
        message="Nieprawidłowa wartość addr:postcode.",
        message_fix="Kod pocztowy powinien być formatu XX-XXX, gdzie X oznacza cyfrę.",
        overpass="['addr:postcode']['addr:postcode'!~'^[0-9]{2}-[0-9]{3}([;,][0-9]{2}-[0-9]{3})*$']"
    ),

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
                    "Jeśli nie, przekaż nazwę miejscowości w addr:place.",
        overpass="['addr:housenumber'][!'addr:city'][!'addr:place']"
    ),

    # NUMBER_WITHOUT_STREET
    Check(
        message="Adres jest niekompletny, brakuje informacji o nazwie ulicy.",
        message_fix="Jeśli adres ma nazwę ulicy, dodaj ją w addr:street. "
                    "Jeśli nie, zamień addr:city na addr:place - tak oznaczamy adresy bez ulic.",
        overpass="['addr:housenumber']['addr:city'][!'addr:street']"
    ),

    # PLACE_WITH_STREET
    Check(
        message="Klucz addr:place oznacza brak nazwy ulicy. "
                "Kombinacja z addr:street (który definiuje nazwę ulicy) jest błędna.",
        message_fix="Jeśli adres ma nazwę ulicy, zamień addr:place na addr:city. "
                    "Jeśli nie, usuń addr:street.",
        overpass="['addr:place']['addr:street']"
    ),

]

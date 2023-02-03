from check import Check

# noinspection SpellCheckingInspection
ALL_CHECKS = [

    # BAD_CITY_WITH_PLACE
    Check(
        priority=50,
        message="Wartość addr:city jest niezgodna z addr:place.",
        message_fix="Jeśli adres ma nazwę ulicy, usuń addr:place i zastosuj kombinację addr:city + addr:street. "
                    "Jeśli nie, pozostaw tylko addr:place.",
        overpass="nwr.p['addr:city'](if: t['addr:city'] != t['addr:place'])",
        overpass_raw=True,
        post_fn=lambda o, i: o.query_place_not_in_area(i, mistype_mode=False)
    ),

    # BAD_POSTCODE_FORMAT
    Check(
        priority=100,
        message="Nieprawidłowa wartość addr:postcode.",
        message_fix="Kod pocztowy powinien być formatu XX-XXX, gdzie X oznacza cyfrę.",
        overpass="['addr:postcode']['addr:postcode'!~'^[0-9]{2}-[0-9]{3}([;,][0-9]{2}-[0-9]{3})*$']"
    ),

    # DUPLICATED
    Check(
        priority=0,
        message="Duplikat adresu w okolicy.",
        message_fix="Adres można oznaczyć na dwa sposoby: na obszarze (dokładniejsze) albo na punkcie. "
                    "Aktualizując adres, należy się upewnić, czy w okolicy nie pozostały żadne duplikaty.",
        overpass=".h",
        overpass_raw=True,
        post_fn=lambda o, i: o.query_duplicates(i)
    ),

    # NUMBER_WITHOUT_CITY
    Check(
        priority=30,
        message="Adres jest niekompletny, brakuje informacji o miejscowości.",
        message_fix="Jeśli adres ma nazwę ulicy, zastosuj kombinację addr:city + addr:street. "
                    "Jeśli nie, przekaż nazwę miejscowości w addr:place.",
        overpass="nwr.h[!'addr:city'][!'addr:place']",
        overpass_raw=True,
    ),

    # NUMBER_WITHOUT_STREET
    Check(
        priority=30,
        message="Adres jest niekompletny, brakuje informacji o nazwie ulicy.",
        message_fix="Jeśli adres ma nazwę ulicy, dodaj ją w addr:street. "
                    "Jeśli nie, zamień addr:city na addr:place - tak oznaczamy adresy bez ulic.",
        overpass="nwr.h['addr:city'][!'addr:street']",
        overpass_raw=True,
    ),

    # TODO: more mistype checks
    # PLACE_MISTYPE
    Check(
        priority=80,
        message="Wartość addr:place zawiera błąd w pisowni.",
        message_fix="Upewnij się, czy wielkość liter jest poprawna, oraz czy nigdzie nie ma dodatkowych znaków.",
        overpass=".p",
        overpass_raw=True,
        post_fn=lambda o, i: o.query_place_not_in_area(i, mistype_mode=True)
    ),

    # PLACE_WITH_STREET
    Check(
        priority=100,
        message="Klucz addr:place oznacza brak nazwy ulicy. "
                "Kombinacja z addr:street (który definiuje nazwę ulicy) jest błędna.",
        message_fix="Jeśli adres ma nazwę ulicy, zamień addr:place na addr:city. "
                    "Jeśli nie, usuń addr:street.",
        overpass="nwr.s['addr:place']",
        overpass_raw=True,
    ),

    # UNKNOWN_STREET_NAME
    Check(
        priority=10,
        message="Nazwa ulicy nie istnieje w okolicy.",
        message_fix="Jeśli adres ma nazwę ulicy, upewnij się, że jest ona poprawna. "
                    "Jeśli nie, usuń addr:street, a nazwę miejscowości przekaż w addr:place.",
        overpass=".s",
        overpass_raw=True,
        post_fn=lambda o, i: o.query_street_names(i)
    ),

]

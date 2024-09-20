from astropy.io.votable import ucd

from app import entities
from app.domain.converters import errors


def get_main_column(columns: list[entities.ColumnDescription], ucd_word: str) -> entities.ColumnDescription:
    id_columns = []
    main_id_columns = []

    for column in columns:
        if column.ucd is None:
            continue

        words = ucd.parse_ucd(column.ucd)

        if len(words) == 0:
            continue

        if words[0][1] == ucd_word:
            id_columns.append(column)

            if len(words) > 1 and words[1][1] == "meta.main":
                main_id_columns.append(column)

    if len(main_id_columns) > 1:
        raise errors.ConverterError(
            f"{len(main_id_columns)} {ucd_word};meta.main columns specified, no more than 1 expected"
        )

    if len(main_id_columns) == 1:
        return main_id_columns[0]

    if len(id_columns) > 1:
        raise errors.ConverterError(f"{len(id_columns)} {ucd_word} columns specified, no more than 1 expected")

    if len(id_columns) == 0:
        raise errors.ConverterNoColumnError(f"No {ucd_word} columns specified")

    return id_columns[0]

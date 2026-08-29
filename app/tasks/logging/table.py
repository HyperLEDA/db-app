from collections.abc import Sequence

import pandas


def print_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str | int]],
    sections: Sequence[tuple[str, Sequence[Sequence[str | int]]]] | None = None,
    min_column_widths: Sequence[int] | None = None,
) -> None:
    columns = list(headers)
    col_space: dict[str, int] | None = None
    if min_column_widths is not None:
        col_space = {column: width for column, width in zip(columns, min_column_widths, strict=False) if width} or None

    def _print_rows(data: Sequence[Sequence[str | int]]) -> None:
        frame = pandas.DataFrame(list(data), columns=columns)
        print(frame.to_string(index=False, col_space=col_space))

    _print_rows(rows)
    if not sections:
        return
    for title, section_rows in sections:
        print()
        print(title)
        _print_rows(section_rows)

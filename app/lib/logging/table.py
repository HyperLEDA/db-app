from collections.abc import Sequence


def print_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str | int]],
    sections: Sequence[tuple[str, Sequence[Sequence[str | int]]]] | None = None,
    min_column_widths: Sequence[int] | None = None,
) -> None:
    ncols = len(headers)
    min_widths = list(min_column_widths) if min_column_widths else [0] * ncols
    while len(min_widths) < ncols:
        min_widths.append(0)

    def cell_str(c: str | int) -> str:
        return str(c)

    def col_width(col_index: int, extra_rows: Sequence[Sequence[str | int]]) -> int:
        candidates = [len(headers[col_index]), min_widths[col_index]]
        for row in rows:
            candidates.append(len(cell_str(row[col_index])))
        if sections:
            for title, section_rows in sections:
                if col_index == 0:
                    candidates.append(len(title))
                for row in section_rows:
                    candidates.append(len(cell_str(row[col_index])))
        for row in extra_rows:
            candidates.append(len(cell_str(row[col_index])))
        return max(candidates)

    widths = [col_width(i, ()) for i in range(ncols)]
    alignments = ["<"] + [">"] * (ncols - 1)

    def sep_line() -> str:
        return "+" + "+".join("-" * (w + 2) for w in widths) + "+"

    def data_line(cells: Sequence[str | int], align: Sequence[str] | None = None) -> str:
        al = align if align else alignments
        return "| " + " | ".join(f"{cell_str(c):{al[i]}{widths[i]}}" for i, c in enumerate(cells)) + " |"

    lines = [sep_line(), data_line(headers), sep_line()]
    for row in rows:
        lines.append(data_line(row))
    lines.append(sep_line())

    if sections:
        for title, section_rows in sections:
            lines.append(data_line([title] + [""] * (ncols - 1)))
            for row in section_rows:
                lines.append(data_line(row))
            lines.append(sep_line())

    for line in lines:
        print(line)

from psycopg import sql


def row_filter_clause(raw: str | None) -> sql.Composed | None:
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    # psycopg treats % as a placeholder marker in the query string.
    return sql.SQL("({})").format(sql.SQL(text.replace("%", "%%")))

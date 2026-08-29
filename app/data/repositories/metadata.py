from dataclasses import dataclass
from typing import Any, final

from app.lib.storage import postgres as pg_storage


@dataclass
class QueryColumnMetadata:
    column_name: str
    sample_value: object | None


@dataclass
class QueryWithMetadataResult:
    columns: list[QueryColumnMetadata]
    rows: list[list[Any]]


def _infer_column_sample(column: str, rows: list[dict[str, Any]]) -> object | None:
    for row in rows:
        value = row[column]
        if value is not None:
            return value
    return None


_TAP_SYNC_QUERY_TIMEOUT_SECONDS = 20


@final
class MetadataRepository(pg_storage.TransactionalPGRepository):
    def __init__(self, storage: pg_storage.PgStorage) -> None:
        super().__init__(storage)

    def query_with_metadata(
        self,
        query: str,
        max_rows: int,
        *,
        timeout_seconds: float = _TAP_SYNC_QUERY_TIMEOUT_SECONDS,
    ) -> QueryWithMetadataResult:
        stripped = query.strip().rstrip(";")
        wrapped = f"SELECT * FROM ({stripped}\n) AS _tap_sync\nLIMIT {max_rows}"
        dict_rows: list[dict[str, Any]] = self._storage.query(
            wrapped,
            timeout_seconds=timeout_seconds,
            read_only=True,
        )
        if not dict_rows:
            return QueryWithMetadataResult(columns=[], rows=[])
        col_names = list(dict_rows[0].keys())
        columns = [
            QueryColumnMetadata(column_name=name, sample_value=_infer_column_sample(name, dict_rows))
            for name in col_names
        ]
        result_rows = [[row[name] for name in col_names] for row in dict_rows]
        return QueryWithMetadataResult(columns=columns, rows=result_rows)

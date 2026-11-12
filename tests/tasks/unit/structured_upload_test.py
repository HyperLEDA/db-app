from typing import Any
from uuid import UUID

import pydantic
import pytest
import structlog

from app.catalogs import layer0, layer1
from app.lib.storage import postgres
from app.specs import adminapi as spec
from app.tasks import artifacts, structured_upload


def _column(name: str, data_type: str, *, unit: str | None = None, not_null: bool = True) -> postgres.ColumnInfo:
    return postgres.ColumnInfo(name=name, data_type=data_type, unit=unit, not_null=not_null)


def _table(schema: str, name: str, columns: list[postgres.ColumnInfo]) -> postgres.TableInfo:
    return postgres.TableInfo(schema=schema, name=name, columns={column.name: column for column in columns})


class _Repo:
    def __init__(
        self, tables: dict[tuple[str, str], postgres.TableInfo], rows: list[dict[str, Any]], total: int
    ) -> None:
        self.tables = tables
        self.rows = rows
        self.total = total
        self.saved: list[tuple[Any, ...]] = []

    def get_table_metadata(self, schema: str, table: str) -> postgres.TableInfo:
        return self.tables[(schema, table)]

    def get_table_record_count(self, table_name: str) -> int:
        return self.total

    def fetch_rawdata_batch(
        self,
        table_name: str,
        columns: list[str],
        limit: int,
        offset: str,
    ) -> list[dict[str, Any]]:
        del table_name, columns, limit
        if offset:
            return []
        return self.rows

    def save_structured_data(
        self, catalog: layer1.Catalog, columns: list[str], ids: list[str], data: list[list[Any]]
    ) -> None:
        self.saved.append((catalog, columns, ids, data))


def _run(
    catalog: layer1.Catalog,
    repo: _Repo,
    params: dict[str, Any],
) -> tuple[list[float], list[list[dict[str, Any]]]]:
    progress: list[float] = []
    previews: list[list[dict[str, Any]]] = []
    task = structured_upload.StructuredCatalogUploadTask(
        structlog.get_logger(),
        catalog,
        params,
        on_progress=lambda value, _: progress.append(value),
        on_preview_table=lambda rows, _: previews.append(rows),
    )
    task.repository = repo
    task.run()
    return progress, previews


def test_params_model_requires_expressions_and_defaults_write() -> None:
    schema = spec.CatalogSchema(
        catalog="icrs",
        title="ICRS",
        description="positions",
        fields=[
            spec.CatalogField(name="ra", data_type=spec.DatatypeEnum["float"], unit="deg", required=True),
            spec.CatalogField(name="note", data_type=spec.DatatypeEnum["str"], required=False),
        ],
    )
    model = structured_upload.build_catalog_params_model(schema)
    with pytest.raises(pydantic.ValidationError):
        model.model_validate({"table_name": "raw", "ra": "col("})
    form = model.model_validate({"table_name": "raw", "ra": 'col("ra")'})
    assert form.note == ""
    assert form.write is False
    assert form.batch_size == 10_000


def test_text_upload_skips_nulls_and_previews_without_writing() -> None:
    repo = _Repo(
        {
            ("designation", "data"): _table(
                "designation",
                "data",
                [
                    _column("record_id", "text"),
                    _column("design", "text"),
                ],
            ),
            ("rawdata", "raw_design"): _table(
                "rawdata",
                "raw_design",
                [
                    _column(layer0.INTERNAL_ID_COLUMN_NAME, "text"),
                    _column("design", "text", not_null=False),
                ],
            ),
        },
        [
            {layer0.INTERNAL_ID_COLUMN_NAME: "r1", "design": "NGC 1"},
            {layer0.INTERNAL_ID_COLUMN_NAME: "r2", "design": None},
            {layer0.INTERNAL_ID_COLUMN_NAME: "r3", "design": "IC 10"},
        ],
        total=3,
    )
    progress, previews = _run(
        layer1.Catalog.DESIGNATION,
        repo,
        {"table_name": "raw_design", "design": 'col("design")', "write": False, "batch_size": 10},
    )
    assert repo.saved == []
    assert previews == [[{"id": "r1", "design": "NGC 1"}, {"id": "r3", "design": "IC 10"}]]
    assert progress == [0, 99, 100]


def test_numeric_upload_converts_units_and_writes() -> None:
    repo = _Repo(
        {
            ("icrs", "data"): _table(
                "icrs",
                "data",
                [_column("ra", "double precision", unit="deg")],
            ),
            ("rawdata", "raw_icrs"): _table(
                "rawdata",
                "raw_icrs",
                [
                    _column(layer0.INTERNAL_ID_COLUMN_NAME, "text"),
                    _column("ra", "double precision", unit="arcmin", not_null=False),
                ],
            ),
        },
        [
            {layer0.INTERNAL_ID_COLUMN_NAME: "r1", "ra": 60.0},
            {layer0.INTERNAL_ID_COLUMN_NAME: "r2", "ra": None},
        ],
        total=2,
    )
    progress, previews = _run(
        layer1.Catalog.ICRS,
        repo,
        {"table_name": "raw_icrs", "ra": 'col("ra")', "write": True, "batch_size": 10},
    )
    assert previews == []
    assert len(repo.saved) == 1
    catalog, columns, ids, data = repo.saved[0]
    assert catalog is layer1.Catalog.ICRS
    assert columns == ["ra"]
    assert ids == ["r1"]
    assert data[0][0] == pytest.approx(1)
    assert progress == [0, 99, 100]


def test_progress_tracker_updates_the_same_artifact(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[dict[str, Any]] = []
    updated: list[dict[str, Any]] = []
    artifact_id = UUID(int=1)

    def create_progress_artifact(**kwargs: Any) -> UUID:
        created.append(kwargs)
        return artifact_id

    def update_progress_artifact(**kwargs: Any) -> UUID:
        updated.append(kwargs)
        return artifact_id

    monkeypatch.setattr(artifacts.artifacts, "create_progress_artifact", create_progress_artifact)
    monkeypatch.setattr(artifacts.artifacts, "update_progress_artifact", update_progress_artifact)
    tracker = artifacts.ProgressTracker()
    tracker.update(0, "start")
    tracker.update(40, "middle")
    assert created[0]["progress"] == 0
    assert updated[0]["artifact_id"] == artifact_id
    assert updated[0]["progress"] == 40


def test_preview_table_artifact(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []

    def create_table_artifact(**kwargs: Any) -> UUID:
        captured.append(kwargs)
        return UUID(int=2)

    monkeypatch.setattr(artifacts.artifacts, "create_table_artifact", create_table_artifact)
    artifacts.emit_preview_table([{"id": "r1", "design": "NGC 1"}], "Dry-run preview")
    assert captured[0]["table"] == [{"id": "r1", "design": "NGC 1"}]
    assert captured[0]["description"] == "Dry-run preview"

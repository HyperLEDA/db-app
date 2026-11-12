from typing import Any
from uuid import UUID

import pydantic
import pytest
import structlog

from app.catalogs import layer0, layer1
from app.lib.storage import postgres
from app.specs import adminapi as spec
from app.tasks import artifacts, formula, structured_upload


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

    def get_rawdata_page_stats(self, table_name: str) -> tuple[int, float]:
        return 1, float(max(1, len(self.rows)))

    def fetch_rawdata_pages(
        self,
        table_name: str,
        columns: list[str],
        start_page: int,
        end_page: int,
    ) -> list[dict[str, Any]]:
        del table_name, columns, end_page
        if start_page > 0:
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


def _field(name: str, data_type: str, unit: str | None = None) -> spec.CatalogField:
    return spec.CatalogField(name=name, data_type=spec.DatatypeEnum[data_type], unit=unit, required=True)


def _evaluate(
    expressions: dict[str, str],
    fields: list[spec.CatalogField],
    rows: list[dict[str, Any]],
    column_units: dict[str, str] | None = None,
) -> tuple[list[str], list[list[Any]]]:
    return structured_upload._evaluate_batch(  # noqa: SLF001
        rows,
        [field.name for field in fields],
        expressions,
        {name: formula.parse(source) for name, source in expressions.items()},
        {field.name: field for field in fields},
        column_units or {},
    )


def _rows(**columns: list[Any]) -> list[dict[str, Any]]:
    size = len(next(iter(columns.values())))
    return [
        {layer0.INTERNAL_ID_COLUMN_NAME: f"r{i}", **{name: values[i] for name, values in columns.items()}}
        for i in range(size)
    ]


def test_evaluate_batch_skips_nulls_across_all_expressions() -> None:
    ids, data = _evaluate(
        {"ra": 'col("a")', "dec": 'col("b")'},
        [_field("ra", "float"), _field("dec", "float")],
        _rows(a=[1.0, 2.0, None, 4.0], b=[1.0, None, 3.0, 4.0]),
    )
    assert ids == ["r0", "r3"]
    assert data == [[1.0, 1.0], [4.0, 4.0]]


def test_evaluate_batch_broadcasts_scalars_and_casts_ints() -> None:
    ids, data = _evaluate(
        {"ra": "0.1 * arcsec", "n": 'col("a")', "note": '"best"'},
        [_field("ra", "float", "arcsec"), _field("n", "int"), _field("note", "str")],
        _rows(a=[1.9, 2.1]),
    )
    assert ids == ["r0", "r1"]
    assert data == [[pytest.approx(0.1), 1, "best"], [pytest.approx(0.1), 2, "best"]]
    assert isinstance(data[0][1], int)


def test_evaluate_batch_converts_units() -> None:
    _, data = _evaluate(
        {"ra": 'col("a")'},
        [_field("ra", "float", "deg")],
        _rows(a=[60.0, 120.0]),
        {"a": "arcmin"},
    )
    assert data == [[pytest.approx(1.0)], [pytest.approx(2.0)]]


def test_evaluate_batch_text_formatting_and_concatenation() -> None:
    _, data = _evaluate(
        {"a": 'str(col("x"))', "b": 'col("s") + "x"', "c": '"x" + col("s")', "d": 'where(col("s") == "p", "G", "*")'},
        [_field("a", "str"), _field("b", "str"), _field("c", "str"), _field("d", "str")],
        _rows(x=[2.0, 2.5], s=["p", "q"]),
    )
    assert data == [["2", "px", "xp", "G"], ["2.5", "qx", "xq", "*"]]


def test_evaluate_batch_numeric_expression_to_text() -> None:
    _, data = _evaluate({"a": 'col("x")'}, [_field("a", "str")], _rows(x=[2.0, 2.5]))
    assert data == [["2"], ["2.5"]]


def test_evaluate_batch_to_deg_uses_text_column_unit() -> None:
    _, data = _evaluate(
        {"ra": 'to_deg(col("ra_text"))'},
        [_field("ra", "float", "deg")],
        _rows(ra_text=["01 00 00", "12 00 00"]),
        {"ra_text": "hourangle"},
    )
    assert data == [[pytest.approx(15.0)], [pytest.approx(180.0)]]


def test_evaluate_batch_non_finite_error_names_record() -> None:
    with pytest.raises(RuntimeError, match=r"'x'.*2 non-finite.*r1.*a=-1.0"):
        _evaluate(
            {"x": 'log10(col("a"))'},
            [_field("x", "float")],
            _rows(a=[1.0, -1.0, 0.0]),
        )


def test_evaluate_batch_division_by_zero_is_non_finite_error() -> None:
    with pytest.raises(RuntimeError, match="non-finite"):
        _evaluate({"x": '1 / col("a")'}, [_field("x", "float")], _rows(a=[0.0]))


def test_evaluate_batch_reports_unit_conversion_failure() -> None:
    with pytest.raises(RuntimeError, match="failed to convert 'ra'"):
        _evaluate({"ra": 'col("a")'}, [_field("ra", "float", "deg")], _rows(a=[1.0]), {"a": "km"})

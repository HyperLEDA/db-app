from typing import Any
from uuid import UUID

import pydantic
import pytest
import structlog

from app.catalogs import layer0, layer1
from app.lib.storage import postgres
from app.specs import adminapi as spec
from app.tasks import artifacts, formula, structured_upload


def _col(name: str, data_type: str, *, unit: str | None = None, not_null: bool = True) -> postgres.ColumnInfo:
    return postgres.ColumnInfo(name=name, data_type=data_type, unit=unit, not_null=not_null)


def _table(schema: str, name: str, columns: list[postgres.ColumnInfo]) -> postgres.TableInfo:
    return postgres.TableInfo(schema=schema, name=name, columns={c.name: c for c in columns})


class _Repo:
    def __init__(
        self, tables: dict[tuple[str, str], postgres.TableInfo], rows: list[dict[str, Any]], total: int
    ) -> None:
        self.tables, self.rows, self.total, self.saved = tables, rows, total, []

    def get_table_metadata(self, schema: str, table: str) -> postgres.TableInfo:
        return self.tables[(schema, table)]

    def get_table_record_count(self, table_name: str) -> int:
        return self.total

    def get_rawdata_page_stats(self, table_name: str) -> tuple[int, float]:
        return 1, float(max(1, len(self.rows)))

    def fetch_rawdata_pages(
        self, table_name: str, columns: list[str], start_page: int, end_page: int
    ) -> list[dict[str, Any]]:
        return [] if start_page > 0 else self.rows

    def save_structured_data(
        self, catalog: layer1.Catalog, columns: list[str], ids: list[str], data: list[list[Any]]
    ) -> None:
        self.saved.append((catalog, columns, ids, data))


def _run(
    catalog: layer1.Catalog,
    repo: _Repo,
    params: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[list[float], list[list[dict[str, Any]]]]:
    progress: list[float] = []
    previews: list[list[dict[str, Any]]] = []
    monkeypatch.setattr(artifacts.ProgressTracker, "update", lambda self, value, _: progress.append(value))
    monkeypatch.setattr(artifacts, "emit_preview_table", lambda rows, _: previews.append(rows))
    task = structured_upload.StructuredCatalogUploadTask(structlog.get_logger(), catalog, params)
    task.repository = repo
    task.run()
    return progress, previews


def _field(name: str, data_type: str, unit: str | None = None) -> spec.CatalogField:
    return spec.CatalogField(name=name, data_type=spec.DatatypeEnum[data_type], unit=unit, required=True)


def _rows(**columns: list[Any]) -> list[dict[str, Any]]:
    size = len(next(iter(columns.values())))
    return [{layer0.INTERNAL_ID_COLUMN_NAME: f"r{i}", **{n: v[i] for n, v in columns.items()}} for i in range(size)]


def _evaluate(
    expressions: dict[str, str],
    fields: list[spec.CatalogField],
    rows: list[dict[str, Any]],
    column_units: dict[str, str] | None = None,
) -> tuple[list[str], list[list[Any]]]:
    return structured_upload._evaluate_batch(  # noqa: SLF001
        rows,
        [f.name for f in fields],
        expressions,
        {n: formula.parse(s) for n, s in expressions.items()},
        {f.name: f for f in fields},
        column_units or {},
    )


def test_params_model_and_upload_paths(monkeypatch: pytest.MonkeyPatch) -> None:
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
    assert form.note == "" and form.write is True and form.batch_size == 10_000

    text_repo = _Repo(
        {
            ("designation", "data"): _table("designation", "data", [_col("record_id", "text"), _col("design", "text")]),
            ("rawdata", "raw_design"): _table(
                "rawdata",
                "raw_design",
                [_col(layer0.INTERNAL_ID_COLUMN_NAME, "text"), _col("design", "text", not_null=False)],
            ),
        },
        [
            {layer0.INTERNAL_ID_COLUMN_NAME: "r1", "design": "NGC 1"},
            {layer0.INTERNAL_ID_COLUMN_NAME: "r2", "design": None},
            {layer0.INTERNAL_ID_COLUMN_NAME: "r3", "design": "IC 10"},
        ],
        3,
    )
    progress, previews = _run(
        layer1.Catalog.DESIGNATION,
        text_repo,
        {"table_name": "raw_design", "design": 'col("design")', "write": False, "batch_size": 10},
        monkeypatch,
    )
    assert text_repo.saved == []
    assert previews == [[{"id": "r1", "design": "NGC 1"}, {"id": "r3", "design": "IC 10"}]]
    assert progress == [0, 99, 100]

    num_repo = _Repo(
        {
            ("icrs", "data"): _table("icrs", "data", [_col("ra", "double precision", unit="deg")]),
            ("rawdata", "raw_icrs"): _table(
                "rawdata",
                "raw_icrs",
                [
                    _col(layer0.INTERNAL_ID_COLUMN_NAME, "text"),
                    _col("ra", "double precision", unit="arcmin", not_null=False),
                ],
            ),
        },
        [{layer0.INTERNAL_ID_COLUMN_NAME: "r1", "ra": 60.0}, {layer0.INTERNAL_ID_COLUMN_NAME: "r2", "ra": None}],
        2,
    )
    progress, previews = _run(
        layer1.Catalog.ICRS,
        num_repo,
        {"table_name": "raw_icrs", "ra": 'col("ra")', "write": True, "batch_size": 10},
        monkeypatch,
    )
    catalog, columns, ids, data = num_repo.saved[0]
    assert previews == [] and (catalog, columns, ids) == (layer1.Catalog.ICRS, ["ra"], ["r1"])
    assert data[0][0] == pytest.approx(1) and progress == [0, 99, 100]


def test_progress_and_preview_artifacts(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[dict[str, Any]] = []
    updated: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    artifact_id = UUID(int=1)
    monkeypatch.setattr(artifacts.artifacts, "create_progress_artifact", lambda **kw: created.append(kw) or artifact_id)
    monkeypatch.setattr(artifacts.artifacts, "update_progress_artifact", lambda **kw: updated.append(kw) or artifact_id)
    monkeypatch.setattr(artifacts.artifacts, "create_table_artifact", lambda **kw: tables.append(kw) or UUID(int=2))
    tracker = artifacts.ProgressTracker()
    tracker.update(0, "start")
    tracker.update(40, "middle")
    assert created[0]["progress"] == 0 and updated[0]["artifact_id"] == artifact_id and updated[0]["progress"] == 40
    artifacts.emit_preview_table([{"id": "r1", "design": "NGC 1"}], "Dry-run preview")
    assert tables[0]["table"] == [{"id": "r1", "design": "NGC 1"}] and tables[0]["description"] == "Dry-run preview"


@pytest.mark.parametrize(
    "case",
    [
        (
            {"ra": 'col("a")', "dec": 'col("b")'},
            [_field("ra", "float"), _field("dec", "float")],
            _rows(a=[1.0, 2.0, None, 4.0], b=[1.0, None, 3.0, 4.0]),
            None,
            ["r0", "r3"],
            [[1.0, 1.0], [4.0, 4.0]],
        ),
        (
            {"ra": "0.1 * arcsec", "n": 'col("a")', "note": '"best"'},
            [_field("ra", "float", "arcsec"), _field("n", "int"), _field("note", "str")],
            _rows(a=[1.9, 2.1]),
            None,
            ["r0", "r1"],
            [[pytest.approx(0.1), 1, "best"], [pytest.approx(0.1), 2, "best"]],
        ),
        (
            {"ra": 'col("a")'},
            [_field("ra", "float", "deg")],
            _rows(a=[60.0, 120.0]),
            {"a": "arcmin"},
            ["r0", "r1"],
            [[pytest.approx(1.0)], [pytest.approx(2.0)]],
        ),
        (
            {
                "a": 'str(col("x"))',
                "b": 'col("s") + "x"',
                "c": '"x" + col("s")',
                "d": 'where(col("s") == "p", "G", "*")',
            },
            [_field("a", "str"), _field("b", "str"), _field("c", "str"), _field("d", "str")],
            _rows(x=[2.0, 2.5], s=["p", "q"]),
            None,
            ["r0", "r1"],
            [["2", "px", "xp", "G"], ["2.5", "qx", "xq", "*"]],
        ),
        ({"a": 'col("x")'}, [_field("a", "str")], _rows(x=[2.0, 2.5]), None, ["r0", "r1"], [["2"], ["2.5"]]),
        (
            {"ra": 'to_deg(col("ra_text"))'},
            [_field("ra", "float", "deg")],
            _rows(ra_text=["01 00 00", "12 00 00"]),
            {"ra_text": "hourangle"},
            ["r0", "r1"],
            [[pytest.approx(15.0)], [pytest.approx(180.0)]],
        ),
    ],
)
def test_evaluate_batch_cases(case: tuple[Any, ...]) -> None:
    expressions, fields, rows, units, expected_ids, expected_data = case
    ids, data = _evaluate(expressions, fields, rows, units)
    assert ids == expected_ids and data == expected_data
    if "n" in expressions:
        assert isinstance(data[0][1], int)


@pytest.mark.parametrize(
    ("expressions", "fields", "rows", "units", "match"),
    [
        (
            {"x": 'log10(col("a"))'},
            [_field("x", "float")],
            _rows(a=[1.0, -1.0, 0.0]),
            None,
            r"'x'.*2 non-finite.*r1.*a=-1.0",
        ),
        ({"x": '1 / col("a")'}, [_field("x", "float")], _rows(a=[0.0]), None, "non-finite"),
        ({"ra": 'col("a")'}, [_field("ra", "float", "deg")], _rows(a=[1.0]), {"a": "km"}, "failed to convert 'ra'"),
    ],
)
def test_evaluate_batch_errors(
    expressions: dict[str, str],
    fields: list[spec.CatalogField],
    rows: list[dict[str, Any]],
    units: dict[str, str] | None,
    match: str,
) -> None:
    with pytest.raises(RuntimeError, match=match):
        _evaluate(expressions, fields, rows, units)

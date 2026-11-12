import datetime
import enum
from typing import Annotated, Any

import pydantic

from app.lib.storage import enums, mapping, postgres

DatatypeEnum = enum.StrEnum(
    "DatatypeEnum",
    zip(mapping.type_map.keys(), mapping.type_map.keys(), strict=False),
)


class WriteRequest(pydantic.BaseModel):
    action_description: str = pydantic.Field(
        default="",
        description="Description of the script/run with input parameters (e.g. table name, column name, etc).",
    )


def check_column_name(column_name: str) -> str:
    if column_name == "hyperleda_internal_id":
        raise ValueError(f"Forbidden column name: {column_name}")

    return column_name


class ColumnDescription(pydantic.BaseModel):
    name: Annotated[str, pydantic.AfterValidator(func=check_column_name)]
    data_type: DatatypeEnum
    ucd: str | None = None
    unit: str | None = None
    description: str | None = None


class Bibliography(pydantic.BaseModel):
    title: str
    authors: list[str]
    year: int
    bibcode: str


class GetTableRequest(pydantic.BaseModel):
    table_name: str


class GetTableListRequest(pydantic.BaseModel):
    query: str = ""
    page_size: int = 25
    page: int = 0
    statuses: list[enums.TableStatus] = pydantic.Field(
        default_factory=lambda: [enums.TableStatus.INITIATED],
    )


class CatalogProgress(pydantic.BaseModel):
    structured: int


class ColumnProgress(pydantic.BaseModel):
    non_null_count: int
    min: int | float | str | bool | None = None
    max: int | float | str | bool | None = None


class TableProgress(pydantic.BaseModel):
    total_records: int
    unprocessed: int
    pending_triage: int
    resolved_unsubmitted: int
    submitted: int
    catalogs: dict[str, CatalogProgress]
    columns: dict[str, ColumnProgress] = pydantic.Field(default_factory=dict)


class TableListItem(pydantic.BaseModel):
    name: str
    description: str
    note: str | None = None
    num_entries: int
    num_fields: int
    modification_dt: datetime.datetime
    bibcode: str
    status: enums.TableStatus
    progress: TableProgress


class GetTableListResponse(pydantic.BaseModel):
    tables: list[TableListItem]


class GetTableResponse(pydantic.BaseModel):
    id: int
    description: str
    note: str | None = None
    column_info: list[ColumnDescription]
    meta: dict[str, Any]
    bibliography: Bibliography
    progress: TableProgress


class CreateTableRequest(WriteRequest):
    table_name: str
    columns: list[ColumnDescription] = pydantic.Field(
        description="List of columns in the table",
        examples=[
            [
                ColumnDescription(name="name", data_type=DatatypeEnum["str"], ucd="meta.id"),
                ColumnDescription(name="ra", data_type=DatatypeEnum["float"], unit="hourangle", ucd="pos.eq.ra"),
                ColumnDescription(name="dec", data_type=DatatypeEnum["float"], unit="deg", ucd="pos.eq.dec"),
            ]
        ],
    )
    bibcode: str = pydantic.Field(
        description="ADS bibcode of the article that published the data (or code of the internal communication)",
        examples=["2024PDU....4601628D"],
    )
    datatype: enums.DataType
    description: str = pydantic.Field(description="Human-readable description of the table")
    note: str | None = pydantic.Field(
        default=None,
        description="Longer free-form textual note about the table",
    )


class CreateTableResponse(pydantic.BaseModel):
    id: int


class AddDataRequest(WriteRequest):
    table_name: str
    data: list[dict[str, Any]] = pydantic.Field(
        description="""Actual data to append. 
Keys in this dictionary must be a subset of the columns in the table. If not specified, column will be set to NULL.
NaN and NULL are considered to be the same thing.""",
        examples=[
            [
                {"name": "M 31", "ra": 0.7123, "dec": 41.2690},
                {"name": "M 33", "ra": 1.5641, "dec": 30.6602},
            ]
        ],
    )


class AddDataResponse(pydantic.BaseModel):
    pass


class SaveStructuredDataRequest(WriteRequest):
    catalog: str
    columns: list[str]
    units: dict[str, str] = {}
    ids: list[str]
    data: list[list[Any]]


class SaveStructuredDataResponse(pydantic.BaseModel):
    pass


class PatchColumnSpec(pydantic.BaseModel):
    ucd: str | None = None
    unit: str | None = None
    description: str | None = None


class PatchTableRequest(WriteRequest):
    table_name: str
    new_table_name: str | None = pydantic.Field(
        default=None,
        description="When set, renames the table.",
    )
    description: str | None = pydantic.Field(
        default=None,
        description="When set, replaces the human-readable description of the table",
    )
    note: str | None = pydantic.Field(
        default=None,
        description="When set, replaces the longer free-form note about the table",
    )
    datatype: enums.DataType | None = pydantic.Field(
        default=None,
        description="When set, replaces the table datatype.",
    )
    status: enums.TableStatus | None = pydantic.Field(
        default=None,
        description="When set, replaces the table status.",
    )
    columns: dict[str, PatchColumnSpec] = {}


class PatchTableResponse(pydantic.BaseModel):
    pass


class CreateSourceRequest(WriteRequest):
    title: str
    authors: list[str] = pydantic.Field(examples=[["Ivanov V.", "Johnson H."]])
    year: int = pydantic.Field(examples=[2006])


class CreateSourceResponse(pydantic.BaseModel):
    code: str


class LoginRequest(pydantic.BaseModel):
    username: str
    password: str


class LoginResponse(pydantic.BaseModel):
    token: str = pydantic.Field(
        description="Token used to authenticate user in handlers that require a specific role to access",
    )


class LogoutRequest(pydantic.BaseModel):
    pass


class LogoutResponse(pydantic.BaseModel):
    pass


class RegisterRequest(pydantic.BaseModel):
    username: str
    email: str
    password: str


class RegisterResponse(pydantic.BaseModel):
    pass


class NewStatusPayload(pydantic.BaseModel):
    record_ids: list[str]
    triage_statuses: list[enums.RecordTriageStatus | None] = []

    @pydantic.model_validator(mode="after")
    def check_triage_length(self) -> "NewStatusPayload":
        if self.triage_statuses and len(self.triage_statuses) != len(self.record_ids):
            raise ValueError("triage_statuses must have the same length as record_ids")
        return self


class ExistingStatusPayload(pydantic.BaseModel):
    record_ids: list[str]
    pgcs: list[int]
    triage_statuses: list[enums.RecordTriageStatus | None] = []

    @pydantic.model_validator(mode="after")
    def check_lengths(self) -> "ExistingStatusPayload":
        if len(self.pgcs) != len(self.record_ids):
            raise ValueError("pgcs must have the same length as record_ids")
        if self.triage_statuses and len(self.triage_statuses) != len(self.record_ids):
            raise ValueError("triage_statuses must have the same length as record_ids")
        return self


class CollidedStatusPayload(pydantic.BaseModel):
    record_ids: list[str]
    possible_matches: list[list[int]]
    triage_statuses: list[enums.RecordTriageStatus | None] = []

    @pydantic.model_validator(mode="after")
    def check_lengths_and_non_empty(self) -> "CollidedStatusPayload":
        if len(self.possible_matches) != len(self.record_ids):
            raise ValueError("possible_matches must have the same length as record_ids")
        for i, pm in enumerate(self.possible_matches):
            if not pm:
                raise ValueError(f"possible_matches[{i}] must be non-empty (status=collided)")
        if self.triage_statuses and len(self.triage_statuses) != len(self.record_ids):
            raise ValueError("triage_statuses must have the same length as record_ids")
        return self


class StatusesPayload(pydantic.BaseModel):
    new: NewStatusPayload | None = None
    existing: ExistingStatusPayload | None = None
    collided: CollidedStatusPayload | None = None

    @pydantic.model_validator(mode="after")
    def check_at_least_one(self) -> "StatusesPayload":
        if not any([self.new, self.existing, self.collided]):
            raise ValueError("at least one of new, existing, collided must be present")
        if self.new is not None and not self.new.record_ids:
            raise ValueError("new.record_ids must be non-empty when present")
        if self.existing is not None and not self.existing.record_ids:
            raise ValueError("existing.record_ids must be non-empty when present")
        if self.collided is not None and not self.collided.record_ids:
            raise ValueError("collided.record_ids must be non-empty when present")
        return self


class SetCrossmatchResultsRequest(WriteRequest):
    statuses: StatusesPayload


class SetCrossmatchResultsResponse(pydantic.BaseModel):
    pass


MAX_ASSIGN_RECORD_PGC_IDS = 200_000


class RecordPgcAssignment(pydantic.BaseModel):
    record_id: str
    pgc: int | None = None


class AssignRecordPgcsRequest(WriteRequest):
    record_ids: list[str] | None = None
    assignments: list[RecordPgcAssignment] | None = None

    @pydantic.model_validator(mode="after")
    def check_modes(self) -> "AssignRecordPgcsRequest":
        has_record_ids = bool(self.record_ids)
        has_assignments = bool(self.assignments)
        if has_record_ids == has_assignments:
            raise ValueError("exactly one of record_ids or assignments must be provided")
        if self.record_ids is not None:
            if len(self.record_ids) > MAX_ASSIGN_RECORD_PGC_IDS:
                raise ValueError(f"record_ids must not exceed {MAX_ASSIGN_RECORD_PGC_IDS}")
        if self.assignments is not None:
            if len(self.assignments) > MAX_ASSIGN_RECORD_PGC_IDS:
                raise ValueError(f"assignments must not exceed {MAX_ASSIGN_RECORD_PGC_IDS}")
            record_ids = [item.record_id for item in self.assignments]
            if len(record_ids) != len(set(record_ids)):
                raise ValueError("assignments must not contain duplicate record_ids")
        return self


class AssignRecordPgcsResponse(pydantic.BaseModel):
    pass


class MergePgcsRequest(WriteRequest):
    target_pgc: int
    source_pgcs: list[int] = pydantic.Field(min_length=1)

    @pydantic.model_validator(mode="after")
    def check_sources(self) -> "MergePgcsRequest":
        if self.target_pgc in self.source_pgcs:
            raise ValueError("target_pgc must not appear in source_pgcs")

        if len(self.source_pgcs) != len(set(self.source_pgcs)):
            raise ValueError("source_pgcs must not contain duplicates")

        return self


class MergePgcsResponse(pydantic.BaseModel):
    target_pgc: int
    merged_pgcs: list[int]
    reassigned_records: int


class CatalogField(pydantic.BaseModel):
    name: str
    data_type: DatatypeEnum
    unit: str | None = None
    required: bool = True
    ucd: str | None = None
    description: str = ""


def field_from_column(col: postgres.ColumnInfo) -> CatalogField:
    return CatalogField(
        name=col.name,
        data_type=postgres_type_to_datatype(col.data_type),
        unit=col.unit,
        required=col.not_null,
        ucd=col.ucd,
        description=str(col.description) if col.description else "",
    )


class CatalogSchema(pydantic.BaseModel):
    catalog: str
    title: str
    description: str
    fields: list[CatalogField]


class GetCatalogsResponse(pydantic.BaseModel):
    catalogs: list[CatalogSchema]


def postgres_type_to_datatype(pg_type: str) -> DatatypeEnum:
    normalized = pg_type.lower().strip()
    if normalized == "array":
        return DatatypeEnum["array"]
    if normalized in {"boolean", "bool"}:
        return DatatypeEnum["boolean"]
    if normalized in {"json", "jsonb"}:
        return DatatypeEnum["json"]
    if normalized in {"text", "character varying", "character", "char", "user-defined", "name", "uuid"}:
        return DatatypeEnum["str"]
    if normalized in {"double precision", "real", "numeric", "float4", "float8"}:
        return DatatypeEnum["float"]
    if normalized in {"integer", "smallint", "serial", "int2", "int4"}:
        return DatatypeEnum["int"]
    if normalized in {"bigint", "int8"}:
        return DatatypeEnum["long"]
    if normalized in {
        "timestamp without time zone",
        "timestamp with time zone",
        "date",
        "time without time zone",
    }:
        return DatatypeEnum["timestamp without time zone"]
    if normalized in DatatypeEnum.__members__:
        return DatatypeEnum[normalized]
    raise ValueError(f"unsupported postgres type: {pg_type}")

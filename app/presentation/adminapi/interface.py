import abc
import datetime
import enum
from typing import Annotated, Any

import pydantic
from astropy import units as u

from app.lib.storage import enums, mapping

DatatypeEnum = enum.StrEnum(
    "DatatypeEnum",
    zip(mapping.type_map.keys(), mapping.type_map.keys(), strict=False),
)


def check_unit(unit: str | None) -> str | None:
    if unit is None:
        return unit

    try:
        u.Unit(unit)
    except Exception as e:
        raise ValueError(f"Invalid unit: {unit}") from e

    return unit


def check_column_name(column_name: str) -> str:
    if column_name == "hyperleda_internal_id":
        raise ValueError(f"Forbidden column name: {column_name}")

    return column_name


class ColumnDescription(pydantic.BaseModel):
    name: Annotated[str, pydantic.AfterValidator(func=check_column_name)]
    data_type: DatatypeEnum
    ucd: str | None = None
    unit: Annotated[str | None, pydantic.AfterValidator(func=check_unit)] = None
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


class TableListItem(pydantic.BaseModel):
    name: str
    description: str
    num_entries: int
    num_fields: int
    modification_dt: datetime.datetime


class GetTableListResponse(pydantic.BaseModel):
    tables: list[TableListItem]


class MarkingRule(pydantic.BaseModel):
    catalog: str
    key: str
    columns: dict[str, str]


class GetTableResponse(pydantic.BaseModel):
    id: int
    description: str
    column_info: list[ColumnDescription]
    rows_num: int
    meta: dict[str, Any]
    bibliography: Bibliography
    marking_rules: list[MarkingRule]
    statistics: dict[enums.RecordCrossmatchStatus, int] | None = None


class CreateTableRequest(pydantic.BaseModel):
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


class CreateTableResponse(pydantic.BaseModel):
    id: int


class AddDataRequest(pydantic.BaseModel):
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


class SaveStructuredDataRequest(pydantic.BaseModel):
    catalog: str
    columns: list[str]
    units: dict[str, str] = {}
    ids: list[str]
    data: list[list[Any]]


class SaveStructuredDataResponse(pydantic.BaseModel):
    pass


class ModifierSpec(pydantic.BaseModel):
    name: str
    params: dict[str, Any] = {}


class PatchColumnSpec(pydantic.BaseModel):
    ucd: str | None = None
    unit: str | None = None
    description: str | None = None
    modifiers: list[ModifierSpec] | None = None


class PatchTableRequest(pydantic.BaseModel):
    table_name: str
    columns: dict[str, PatchColumnSpec]


class PatchTableResponse(pydantic.BaseModel):
    pass


class CreateSourceRequest(pydantic.BaseModel):
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


class ParameterToMark(pydantic.BaseModel):
    column_name: str = pydantic.Field(description="Column that this parameter will be mapped to.", examples=["ra"])


class CatalogToMark(pydantic.BaseModel):
    name: str
    parameters: dict[str, ParameterToMark] = pydantic.Field(
        description="Map of parameter names to their configurations",
        examples=[{"ra": ParameterToMark(column_name="ra"), "dec": ParameterToMark(column_name="dec")}],
    )
    key: str | None = pydantic.Field(default=None, examples=[""])
    additional_params: dict[str, Any] | None = {}


class CreateMarkingRequest(pydantic.BaseModel):
    table_name: str
    catalogs: list[CatalogToMark]


class CreateMarkingResponse(pydantic.BaseModel):
    pass


class UploadStatus(enum.Enum):
    UPLOADED = "uploaded"
    PENDING = "pending"


class CrossmatchTriageStatus(enum.Enum):
    UNPROCESSED = "unprocessed"
    PENDING = "pending"
    RESOLVED = "resolved"


class GetRecordsRequest(pydantic.BaseModel):
    table_name: str
    page: int = 0
    page_size: int = 25
    pgc: int | None = None
    upload_status: UploadStatus | None = None
    triage_status: CrossmatchTriageStatus | None = None

    @pydantic.model_validator(mode="after")
    def check_exclusive_pgc_filter(self) -> "GetRecordsRequest":
        if self.pgc is not None:
            if any([self.upload_status is not None, self.triage_status is not None]):
                raise ValueError("When pgc filter is specified, no other filters are allowed.")
        return self

    @pydantic.model_validator(mode="after")
    def check_upload_status_and_triage_status(self) -> "GetRecordsRequest":
        if self.upload_status == UploadStatus.UPLOADED and self.triage_status is not None:
            raise ValueError("When upload_status is UPLOADED, triage_status is not allowed.")
        return self


class RecordCrossmatchCandidate(pydantic.BaseModel):
    pgc: int


class RecordCrossmatchInfo(pydantic.BaseModel):
    triage_status: CrossmatchTriageStatus
    candidates: list[RecordCrossmatchCandidate]


class RecordDesignationCatalog(pydantic.BaseModel):
    name: str


class RecordICRSCatalog(pydantic.BaseModel):
    ra: float
    ra_error: float
    dec: float
    dec_error: float


class RecordRedshiftCatalog(pydantic.BaseModel):
    z: float
    z_error: float


class RecordNatureCatalog(pydantic.BaseModel):
    type_name: str


class RecordCatalogValues(pydantic.BaseModel):
    designation: RecordDesignationCatalog | None
    # icrs: RecordICRSCatalog | None
    # redshift: RecordRedshiftCatalog | None
    # nature: RecordNatureCatalog | None


class Record(pydantic.BaseModel):
    id: str
    original_data: dict[str, Any]
    pgc: int | None
    crossmatch: RecordCrossmatchInfo
    catalogs: RecordCatalogValues


class DescriptionSchema(pydantic.BaseModel):
    original_data: dict[str, str]


class UnitSchema(pydantic.BaseModel):
    original_data: dict[str, str]


class UCDSchema(pydantic.BaseModel):
    original_data: dict[str, str]


class RecordSchema(pydantic.BaseModel):
    description: DescriptionSchema
    unit: UnitSchema
    ucd: UCDSchema


class GetRecordsResponse(pydantic.BaseModel):
    records: list[Record]
    schema_: RecordSchema = pydantic.Field(..., alias="schema")


class GetRecordsCrossmatchRequest(pydantic.BaseModel):
    table_name: str
    status: enums.RecordCrossmatchStatus | None = None
    triage_status: enums.RecordTriageStatus | None = None
    page: int = 0
    page_size: int = 25


class RecordCrossmatchMetadata(pydantic.BaseModel):
    possible_matches: list[int] | None = None
    pgc: int | None = None


class EquatorialCoordinates(pydantic.BaseModel):
    ra: float
    dec: float
    e_ra: float
    e_dec: float


class GalacticCoordinates(pydantic.BaseModel):
    lon: float
    lat: float
    e_lon: float
    e_lat: float


class Coordinates(pydantic.BaseModel):
    equatorial: EquatorialCoordinates
    galactic: GalacticCoordinates


class Designation(pydantic.BaseModel):
    name: str


class Redshift(pydantic.BaseModel):
    z: float
    e_z: float


class HeliocentricVelocity(pydantic.BaseModel):
    v: float
    e_v: float


class Velocity(pydantic.BaseModel):
    heliocentric: HeliocentricVelocity


class Catalogs(pydantic.BaseModel):
    designation: Designation | None = None
    coordinates: Coordinates | None = None
    redshift: Redshift | None = None
    velocity: Velocity | None = None


class RecordCrossmatch(pydantic.BaseModel):
    record_id: str
    status: enums.RecordCrossmatchStatus
    triage_status: enums.RecordTriageStatus
    metadata: RecordCrossmatchMetadata
    catalogs: Catalogs


class UnitsSchema(pydantic.BaseModel):
    coordinates: dict[str, dict[str, str]]
    velocity: dict[str, dict[str, str]]


class Schema(pydantic.BaseModel):
    units: UnitsSchema


class GetRecordsCrossmatchResponse(pydantic.BaseModel):
    records: list[RecordCrossmatch]
    schema_: Schema = pydantic.Field(..., alias="schema")


class GetRecordCrossmatchRequest(pydantic.BaseModel):
    record_id: str


class PGCCandidate(pydantic.BaseModel):
    pgc: int
    catalogs: Catalogs


class GetRecordCrossmatchResponse(pydantic.BaseModel):
    table_name: str
    crossmatch: RecordCrossmatch
    candidates: list[PGCCandidate]
    schema_: Schema = pydantic.Field(..., alias="schema")
    original_data: dict[str, Any] | None = None


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


class SetCrossmatchResultsRequest(pydantic.BaseModel):
    statuses: StatusesPayload


class SetCrossmatchResultsResponse(pydantic.BaseModel):
    pass


class Actions(abc.ABC):
    @abc.abstractmethod
    def add_data(self, request: AddDataRequest) -> AddDataResponse:
        pass

    @abc.abstractmethod
    def create_table(self, request: CreateTableRequest) -> tuple[CreateTableResponse, bool]:
        pass

    @abc.abstractmethod
    def get_table(self, request: GetTableRequest) -> GetTableResponse:
        pass

    @abc.abstractmethod
    def get_table_list(self, request: GetTableListRequest) -> GetTableListResponse:
        pass

    @abc.abstractmethod
    def patch_table(self, request: PatchTableRequest) -> PatchTableResponse:
        pass

    @abc.abstractmethod
    def create_source(self, request: CreateSourceRequest) -> CreateSourceResponse:
        pass

    @abc.abstractmethod
    def login(self, request: LoginRequest) -> LoginResponse:
        pass

    @abc.abstractmethod
    def create_marking(self, request: CreateMarkingRequest) -> CreateMarkingResponse:
        pass

    @abc.abstractmethod
    def get_records(self, request: GetRecordsRequest) -> GetRecordsResponse:
        pass

    @abc.abstractmethod
    def get_crossmatch_records(self, request: GetRecordsCrossmatchRequest) -> GetRecordsCrossmatchResponse:
        pass

    @abc.abstractmethod
    def get_record_crossmatch(self, request: GetRecordCrossmatchRequest) -> GetRecordCrossmatchResponse:
        pass

    @abc.abstractmethod
    def save_structured_data(self, request: SaveStructuredDataRequest) -> SaveStructuredDataResponse:
        pass

    @abc.abstractmethod
    def set_crossmatch_results(self, request: SetCrossmatchResultsRequest) -> SetCrossmatchResultsResponse:
        pass

import abc
import datetime
import enum
from typing import Annotated, Any

import pydantic
from astropy import units as u

from app.lib.storage import enums, mapping


class GetTaskInfoRequest(pydantic.BaseModel):
    task_id: int


class GetTaskInfoResponse(pydantic.BaseModel):
    id: int | None
    task_name: str
    status: str
    payload: dict[str, Any]
    start_time: datetime.datetime | None
    end_time: datetime.datetime | None
    message: dict[str, Any] | None


DatatypeEnum = enum.StrEnum(
    "DatatypeEnum",
    zip(mapping.type_map.keys(), mapping.type_map.keys(), strict=False),
)


def check_unit(unit: str) -> str:
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


class GetTableResponse(pydantic.BaseModel):
    id: int
    description: str
    column_info: list[ColumnDescription]
    rows_num: int
    meta: dict[str, Any]
    bibliography: Bibliography


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
    table_id: int
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


class PatchTableActionTypeChangeUCD(pydantic.BaseModel):
    column: str
    ucd: str


class PatchTableActionTypeChangeUnit(pydantic.BaseModel):
    column: str
    unit: str


class PatchTableRequest(pydantic.BaseModel):
    table_name: str
    actions: list[PatchTableActionTypeChangeUCD | PatchTableActionTypeChangeUnit]


class PatchTableResponse(pydantic.BaseModel):
    pass


class CrossIdentification(pydantic.BaseModel):
    inner_radius_arcsec: float = 1.5
    outer_radius_arcsec: float = 3


class TableStatusStatsRequest(pydantic.BaseModel):
    table_id: int


class TableStatusStatsResponse(pydantic.BaseModel):
    processing: dict[enums.ObjectCrossmatchStatus, int]


class SetTableStatusOverrides(pydantic.BaseModel):
    id: str
    pgc: int | None = None


class SetTableStatusRequest(pydantic.BaseModel):
    table_id: int
    overrides: list[SetTableStatusOverrides] | None = None
    batch_size: int = 100


class SetTableStatusResponse(pydantic.BaseModel):
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
    def patch_table(self, request: PatchTableRequest) -> PatchTableResponse:
        pass

    @abc.abstractmethod
    def create_source(self, request: CreateSourceRequest) -> CreateSourceResponse:
        pass

    @abc.abstractmethod
    def table_status_stats(self, request: TableStatusStatsRequest) -> TableStatusStatsResponse:
        pass

    @abc.abstractmethod
    def get_task_info(self, request: GetTaskInfoRequest) -> GetTaskInfoResponse:
        pass

    @abc.abstractmethod
    def login(self, request: LoginRequest) -> LoginResponse:
        pass

    @abc.abstractmethod
    def create_marking(self, request: CreateMarkingRequest) -> CreateMarkingResponse:
        pass

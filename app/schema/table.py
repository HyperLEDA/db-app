from dataclasses import dataclass
from typing import Any


@dataclass
class ColumnDescription:
    name: str
    data_type: str
    ucd: str | None = None
    unit: str | None = None
    description: str | None = None


@dataclass
class CreateTableRequest:
    table_name: str
    columns: list[ColumnDescription]
    bibcode: str
    datatype: str
    description: str


@dataclass
class CreateTableResponse:
    id: int


@dataclass
class AddDataRequest:
    table_id: int
    data: list[dict[str, Any]]


@dataclass
class AddDataResponse:
    pass


@dataclass
class CrossIdentification:
    inner_radius_arcsec: float
    outer_radius_arcsec: float


@dataclass
class TableProcessRequest:
    table_id: int
    cross_identification: CrossIdentification


@dataclass
class TableProcessResponse:
    pass
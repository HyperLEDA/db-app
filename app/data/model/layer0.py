import datetime
from dataclasses import dataclass

import pandas
from astropy import units as u

from app.data.model import interface
from app.lib.storage import enums


@dataclass
class Layer0RawData:
    table_id: int
    data: pandas.DataFrame


@dataclass
class ColumnDescription:
    name: str
    data_type: str
    is_primary_key: bool = False
    unit: u.Unit | None = None
    description: str | None = None
    ucd: str | None = None


@dataclass
class Layer0TableMeta:
    table_name: str
    column_descriptions: list[ColumnDescription]
    bibliography_id: int
    datatype: enums.DataType = enums.DataType.REGULAR
    modification_dt: datetime.datetime | None = None
    description: str | None = None


@dataclass
class Layer0CreationResponse:
    table_id: int
    created: bool


@dataclass
class Layer0Object:
    object_id: str
    data: list[interface.CatalogObject]


@dataclass
class CIResultObjectNew:
    pass


@dataclass
class CIResultObjectExisting:
    pgc: int


@dataclass
class CIResultObjectCollision:
    possible_pgcs: dict[str, set[int]]


CIResult = CIResultObjectNew | CIResultObjectExisting | CIResultObjectCollision


@dataclass
class Layer0ProcessedObject:
    object_id: str
    data: list[interface.CatalogObject]
    processing_result: CIResult


@dataclass
class TableStatistics:
    statuses: dict[enums.ObjectCrossmatchStatus, int]
    last_modified_dt: datetime.datetime
    total_rows: int
    total_original_rows: int


@dataclass
class HomogenizationRule:
    catalog: str
    parameter: str
    key: str
    filters: dict[str, str]
    priority: int
    enrichment: dict[str, str]


@dataclass
class HomogenizationParams:
    catalog: str
    key: str
    params: dict[str, str]

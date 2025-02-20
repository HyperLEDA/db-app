import datetime
from dataclasses import dataclass
from typing import Any

import pandas
from astropy import units as u

from app.data.model import interface
from app.lib.storage import enums


@dataclass
class Layer0OldObject:
    object_id: str
    status: enums.ObjectProcessingStatus
    metadata: dict[str, Any]
    data: list[interface.CatalogObject]
    pgc: int | None = None


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
    datatype: enums.DataType
    modification_dt: datetime.datetime | None = None
    description: str | None = None


@dataclass
class Layer0CreationResponse:
    table_id: int
    created: bool


@dataclass
class Layer0Object:
    object_id: int
    data: list[interface.CatalogObject]


@dataclass
class TableStatistics:
    statuses: dict[enums.ObjectProcessingStatus, int]
    last_modified_dt: datetime.datetime
    total_rows: int
    total_original_rows: int

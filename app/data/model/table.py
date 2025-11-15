import datetime
from dataclasses import dataclass
from typing import Any

import pandas
from astropy import units as u

from app.lib.storage import enums


@dataclass
class Layer0RawData:
    table_name: str
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
    table_id: int | None = None


@dataclass
class Layer0CreationResponse:
    table_id: int
    created: bool


@dataclass
class TableStatistics:
    statuses: dict[enums.RecordCrossmatchStatus, int]
    last_modified_dt: datetime.datetime
    total_rows: int
    total_original_rows: int


@dataclass
class HomogenizationRule:
    catalog: str
    parameter: str
    filters: dict[str, str]
    key: str = ""
    priority: int | None = None


@dataclass
class HomogenizationParams:
    catalog: str
    params: dict[str, Any]
    key: str = ""


@dataclass
class Modifier:
    column_name: str
    modifier_name: str
    params: dict[str, Any]

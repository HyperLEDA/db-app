import datetime
from dataclasses import dataclass
from typing import Any

import pandas

from app.catalogs.table_statistics import TableProgress
from app.lib.storage import enums, postgres


@dataclass
class Layer0RawData:
    table_name: str
    data: pandas.DataFrame


@dataclass
class TableRecord:
    id: str
    original_data: dict[str, Any]
    pgc: int | None
    triage_status: str
    crossmatch_candidates: list[int]
    table_name: str


@dataclass
class Layer0TableMeta:
    table_info: postgres.TableInfo
    bibliography_id: int
    datatype: enums.DataType = enums.DataType.REGULAR
    status: enums.TableStatus = enums.TableStatus.INITIATED
    modification_dt: datetime.datetime | None = None
    table_id: int | None = None
    statistics: TableProgress | None = None


@dataclass
class Layer0TableListItem:
    table_name: str
    description: str
    num_fields: int
    modification_dt: datetime.datetime
    bibcode: str
    status: enums.TableStatus
    statistics: TableProgress | None = None


@dataclass
class Layer0CreationResponse:
    table_id: int
    created: bool

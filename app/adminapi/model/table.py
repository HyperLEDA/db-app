import datetime
from dataclasses import dataclass
from typing import Any

import pandas

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


@dataclass
class Layer0TableMeta:
    table_info: postgres.TableInfo
    bibliography_id: int
    datatype: enums.DataType = enums.DataType.REGULAR
    status: enums.TableStatus = enums.TableStatus.INITIATED
    modification_dt: datetime.datetime | None = None
    table_id: int | None = None


@dataclass
class Layer0TableListItem:
    table_name: str
    description: str
    num_fields: int
    modification_dt: datetime.datetime
    bibcode: str
    status: enums.TableStatus


@dataclass
class Layer0CreationResponse:
    table_id: int
    created: bool


@dataclass
class CatalogProgress:
    structured: int
    in_layer2: int
    layer2_pending: int


@dataclass
class TableProgress:
    total_records: int
    unprocessed: int
    pending_triage: int
    resolved_unsubmitted: int
    submitted: int
    catalogs: dict[str, CatalogProgress]

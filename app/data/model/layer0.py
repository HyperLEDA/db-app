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
    """
    Metadata about the table to upload to layer 0

    Args:
        `table_name`: name of the table that will be written into database
        `column_descriptions`: information about each column
        `bibliography_id`: id of bibliography
        `description`: description of the table
    """

    table_name: str
    column_descriptions: list[ColumnDescription]
    bibliography_id: int
    datatype: enums.DataType
    description: str | None = None


@dataclass
class Layer0CreationResponse:
    """
    Response from the data layer after the creation of the table.

    Args:
        `table_id`: id of the table in the internal registry
        `created`: False if table with this name already existed, True otherwise
    """

    table_id: int
    created: bool


@dataclass
class Layer0Object:
    object_id: int
    data: list[interface.CatalogObject]

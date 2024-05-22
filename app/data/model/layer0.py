from __future__ import annotations

from dataclasses import dataclass

import pandas

from app.lib.storage import enums


@dataclass
class ColumnDescription:
    name: str
    data_type: str
    unit: str | None = None  # TODO: validate that the unit is one that we know how to transform
    description: str | None = None
    ucd: str | None = None
    coordinate_part: CoordinatePart | None = None


@dataclass
class CoordinatePart:
    """
    Args:
        `descr_id`: string to identify CoordinateDescription
        `arg_num`: Argument number in CoordinateDescription constructor
    """

    descr_id: str
    arg_num: int
    column_name: str


@dataclass
class Layer0Creation:
    """
    Metadata about the table to upload to layer 0

    Args:
        `table_name`: name of the table that will be written into database
        `column_descriptions`: information about each column
        `bibliography_id`: id of bibliography
        `name_col`: Name of column, holding object name
        `comment`: description of the table
    """

    table_name: str
    column_descriptions: list[ColumnDescription]
    bibliography_id: int
    datatype: enums.DataType
    name_col: str | None = None
    comment: str | None = None


@dataclass
class Layer0RawData:
    table_id: int
    data: pandas.DataFrame

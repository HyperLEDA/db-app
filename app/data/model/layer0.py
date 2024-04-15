from dataclasses import dataclass

import pandas

from app.data.model import common


@dataclass
class ColumnDescription:
    name: str
    data_type: str
    unit: str | None = None  # TODO: validate that the unit is one that we know how to transform
    description: str | None = None


@dataclass
class Layer0Creation:
    """
    Metadata about the table to upload to layer 0

    Args:
        `table_name`: name of the table that will be written into database
        `column_descriptions`: information about each column
        `bibliography`: bibliographic information
        `comment`: description of the table
    """

    table_name: str
    column_descriptions: list[ColumnDescription]
    bibliography: common.Bibliography
    comment: str | None = None


@dataclass
class Layer0RawData:
    table_name: str
    data: pandas.DataFrame

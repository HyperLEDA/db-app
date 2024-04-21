from dataclasses import dataclass


@dataclass
class ColumnDescription:
    name: str
    data_type: str
    unit: str
    description: str


@dataclass
class CreateTableRequest:
    table_name: str
    columns: list[ColumnDescription]
    bibliography_id: int
    datatype: str
    description: str


@dataclass
class CreateTableResponse:
    id: int

import enum

import pydantic


class Detail(enum.StrEnum):
    MIN = "min"
    MAX = "max"


class TAPFormat(enum.StrEnum):
    JSON = "json"


class TAPRequestKind(enum.StrEnum):
    DO_QUERY = "doQuery"


class TAPLang(enum.StrEnum):
    POSTGRESQL = "PostgreSQL"


class TAPColumnInfo(pydantic.BaseModel):
    name: str
    datatype: str
    unit: str | None = None
    ucd: str | None = None
    description: str | None = None


class TAPTableInfo(pydantic.BaseModel):
    name: str
    type: str = "table"
    description: str | None = None
    columns: list[TAPColumnInfo] | None = None


class TAPSchemaEntry(pydantic.BaseModel):
    schema_name: str
    tables: list[TAPTableInfo]


class ListTAPTablesRequest(pydantic.BaseModel):
    detail: Detail = Detail.MAX
    format: TAPFormat = TAPFormat.JSON


class ListTAPTablesResponse(pydantic.BaseModel):
    schemas: list[TAPSchemaEntry]


class TAPSyncRequest(pydantic.BaseModel):
    request: TAPRequestKind = TAPRequestKind.DO_QUERY
    lang: TAPLang = TAPLang.POSTGRESQL
    query: str = pydantic.Field(description="SQL query to execute")
    format: TAPFormat = TAPFormat.JSON
    maxrec: int = pydantic.Field(default=50, ge=1, le=10_000)


class TAPVOTableColumn(pydantic.BaseModel):
    name: str
    datatype: str
    arraysize: str | None = None
    unit: str | None = None


class TAPVOTableTable(pydantic.BaseModel):
    columns: list[TAPVOTableColumn]
    data: list[list[object]]


class TAPVOTableResource(pydantic.BaseModel):
    name: str = "TAP Sync Result"
    description: str | None = None
    table: TAPVOTableTable


class TAPSyncResponse(pydantic.BaseModel):
    resource: TAPVOTableResource

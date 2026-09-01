import enum
from typing import Any

import pydantic

from app.specs.adminapi.interface import DatatypeEnum

ReferenceScalar = str | int | float | bool | None
ReferenceValue = ReferenceScalar | list[ReferenceScalar] | dict[str, Any]


class ReferenceInputKind(enum.StrEnum):
    TEXT = "text"
    NUMBER = "number"
    TEXTAREA = "textarea"
    JSON = "json"
    SELECT = "select"
    REFERENCE = "reference"


class ReferenceSelectOption(pydantic.BaseModel):
    value: ReferenceScalar
    label: str
    description: str | None = None


class ReferenceInput(pydantic.BaseModel):
    kind: ReferenceInputKind
    options: list[ReferenceSelectOption] | None = None


class ReferenceFieldDescriptor(pydantic.BaseModel):
    name: str
    description: str | None = None
    data_type: DatatypeEnum
    items_data_type: DatatypeEnum | None = None
    required: bool
    nullable: bool
    input: ReferenceInput


class ReferenceResourceDescriptor(pydantic.BaseModel):
    schema_name: str = pydantic.Field(serialization_alias="schema")
    table: str
    description: str | None = None
    fields: list[ReferenceFieldDescriptor]

    model_config = pydantic.ConfigDict(populate_by_name=True)


class ListReferencesResponse(pydantic.BaseModel):
    references: list[ReferenceResourceDescriptor]


class ListReferenceRowsRequest(pydantic.BaseModel):
    page: int = 0
    page_size: int = 25
    query: str = ""


class ReferenceRowItem(pydantic.BaseModel):
    key: dict[str, ReferenceValue]
    row: dict[str, ReferenceValue]


class ListReferenceRowsResponse(pydantic.BaseModel):
    schema_name: str = pydantic.Field(serialization_alias="schema")
    table: str
    items: list[ReferenceRowItem]
    page: int
    page_size: int
    total: int

    model_config = pydantic.ConfigDict(populate_by_name=True)


class ListReferenceFieldOptionsRequest(pydantic.BaseModel):
    query: str = ""
    page: int = 0
    page_size: int = 25


class ReferenceFieldOption(pydantic.BaseModel):
    value: ReferenceScalar
    label: str
    description: str | None = None


class ListReferenceFieldOptionsResponse(pydantic.BaseModel):
    field: str
    items: list[ReferenceFieldOption]
    page: int
    page_size: int
    total: int


class CreateReferenceRowRequest(pydantic.BaseModel):
    row: dict[str, ReferenceValue]
    action_description: str = pydantic.Field(default="")


class CreateReferenceRowResponse(pydantic.BaseModel):
    pass


class PatchReferenceRowRequest(pydantic.BaseModel):
    key: dict[str, ReferenceValue]
    changes: dict[str, ReferenceValue]
    action_description: str = pydantic.Field(default="")


class PatchReferenceRowResponse(pydantic.BaseModel):
    pass

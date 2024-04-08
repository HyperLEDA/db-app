from dataclasses import dataclass


@dataclass
class SearchCatalogsRequest:
    query: str
    page_size: int


@dataclass
class Field:
    id: str
    description: str
    unit: str


@dataclass
class Table:
    id: str
    fields: list[Field]
    num_rows: int


@dataclass
class Catalog:
    id: str
    description: str
    url: str
    bibcode: str
    tables: list[Table]


@dataclass
class SearchCatalogsResponse:
    catalogs: list[Catalog]

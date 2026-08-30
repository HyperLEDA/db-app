from dataclasses import dataclass
from typing import Any


@dataclass
class ReddeningCoefficient:
    filter: str
    lambda_eff: float
    a_ebv: float


@dataclass
class ReddeningPhotometricSystem:
    id: str
    description: str


@dataclass
class QueryColumnMetadata:
    column_name: str
    sample_value: object | None


@dataclass
class QueryWithMetadataResult:
    columns: list[QueryColumnMetadata]
    rows: list[list[Any]]

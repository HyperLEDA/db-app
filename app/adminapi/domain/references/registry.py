from dataclasses import dataclass


@dataclass(frozen=True)
class ReferenceResourceKey:
    schema: str
    table: str

    def as_tuple(self) -> tuple[str, str]:
        return (self.schema, self.table)


@dataclass(frozen=True)
class ReferenceOptionDisplay:
    label_column: str
    description_columns: tuple[str, ...] = ()


REFERENCE_RESOURCES: tuple[ReferenceResourceKey, ...] = (
    ReferenceResourceKey("distance", "methods"),
    ReferenceResourceKey("distance", "calibrations"),
    ReferenceResourceKey("common", "bib"),
)

REFERENCE_OPTION_DISPLAY: dict[tuple[str, str], ReferenceOptionDisplay] = {
    ("distance", "methods"): ReferenceOptionDisplay(label_column="title", description_columns=("id", "indicator")),
    ("distance", "calibrations"): ReferenceOptionDisplay(label_column="id", description_columns=("method_id",)),
    ("common", "bib"): ReferenceOptionDisplay(label_column="code", description_columns=("year", "title", "author")),
}


def is_allowed_reference(schema: str, table: str) -> bool:
    return any(resource.schema == schema and resource.table == table for resource in REFERENCE_RESOURCES)

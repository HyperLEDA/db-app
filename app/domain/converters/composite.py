from collections.abc import Hashable
from typing import Any, final

from app.domain.converters import errors, interface
from app.entities.layer0 import ColumnDescription
from app.entities.object import ObjectInfo


@final
class CompositeConverter(interface.QuantityConverter):
    """
    Composite converter parses and applies provided converters sequentially.
    It is a convinience converter, that wraps all iteration and work with errors.
    """

    def __init__(self, *convs: interface.QuantityConverter) -> None:
        self.converters = convs

    def name(self) -> str:
        return "composite"

    def parse_columns(self, columns: list[ColumnDescription]) -> None:
        # TODO: fallback if name or one of coordinates are not specified

        for converter in self.converters:
            try:
                converter.parse_columns(columns)
            except errors.ConverterNoColumnError as e:
                raise errors.ConverterNoColumnError(
                    f"Did not find any columns that correspond to the '{converter.name()}' converter"
                ) from e
            except errors.ConverterError as e:
                raise errors.ConverterError(f"Error during validation of '{converter.name()}' converter: {e}") from e

        for conv in self.converters:
            conv.parse_columns(columns)

    def apply(self, object_info: ObjectInfo, data: dict[Hashable, Any]) -> ObjectInfo:
        obj = object_info

        for conv in self.converters:
            obj = conv.apply(obj, data)

        return obj

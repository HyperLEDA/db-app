from typing import Any, Self, final, override

from app.catalogs.layer1 import Catalog as Layer1Catalog
from app.catalogs.layer2 import interface


@final
class GeometryCatalogObject(interface.CatalogObject):
    def __init__(
        self,
        a25: float | None = None,
        b25: float | None = None,
        pa25: float | None = None,
        a_re: float | None = None,
        b_re: float | None = None,
        pa_re: float | None = None,
    ) -> None:
        self.a25 = a25
        self.b25 = b25
        self.pa25 = pa25
        self.a_re = a_re
        self.b_re = b_re
        self.pa_re = pa_re

    @classmethod
    @override
    def catalog(cls) -> interface.Catalog:
        return interface.Catalog.GEOMETRY

    @classmethod
    @override
    def table(cls) -> str:
        return "layer2.geometry"

    @classmethod
    @override
    def sources(cls) -> list[Layer1Catalog]:
        return [Layer1Catalog.GEOMETRY]

    @classmethod
    @override
    def keys(cls) -> list[str]:
        return ["a25", "b25", "pa25", "a_re", "b_re", "pa_re"]

    @override
    def to_row(self) -> dict[str, Any]:
        return {
            "a25": self.a25,
            "b25": self.b25,
            "pa25": self.pa25,
            "a_re": self.a_re,
            "b_re": self.b_re,
            "pa_re": self.pa_re,
        }

    @classmethod
    @override
    def from_row(cls, data: dict[str, Any]) -> Self:
        return cls(
            a25=_optional_float(data["a25"]),
            b25=_optional_float(data["b25"]),
            pa25=_optional_float(data["pa25"]),
            a_re=_optional_float(data["a_re"]),
            b_re=_optional_float(data["b_re"]),
            pa_re=_optional_float(data["pa_re"]),
        )


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)

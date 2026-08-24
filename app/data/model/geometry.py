from typing import Any, final

from app.data.model import interface


@final
class GeometryCatalogObject(interface.CatalogObject):
    def __init__(
        self,
        band: str,
        method: str,
        level: float | None = None,
        a: float | None = None,
        e_a: float | None = None,
        b: float | None = None,
        e_b: float | None = None,
        pa: float | None = None,
        e_pa: float | None = None,
        isophote: float | None = None,
        e_isophote: float | None = None,
        **kwargs: Any,
    ) -> None:
        self.band = band
        self.method = method
        self.level = level
        self.a = a
        self.e_a = e_a
        self.b = b
        self.e_b = e_b
        self.pa = pa
        self.e_pa = e_pa
        self.isophote = isophote
        self.e_isophote = e_isophote

    def catalog(self) -> interface.RawCatalog:
        return interface.RawCatalog.GEOMETRY

    @classmethod
    def title(cls) -> str:
        return "Geometry"

    @classmethod
    def description(cls) -> str:
        return "Isophotal ellipse geometry."

    @classmethod
    def layer1_table(cls) -> str:
        return "photometry.ellipse"

    @classmethod
    def layer1_primary_keys(cls) -> list[str]:
        return ["record_id", "band", "method", "level", "isophote"]

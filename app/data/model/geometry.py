from typing import Any, Self, final

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

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, GeometryCatalogObject):
            return False
        return (
            self.band == value.band
            and self.method == value.method
            and self.level == value.level
            and self.a == value.a
            and self.e_a == value.e_a
            and self.b == value.b
            and self.e_b == value.e_b
            and self.pa == value.pa
            and self.e_pa == value.e_pa
            and self.isophote == value.isophote
            and self.e_isophote == value.e_isophote
        )

    def catalog(self) -> interface.RawCatalog:
        return interface.RawCatalog.GEOMETRY

    @classmethod
    def layer1_table(cls) -> str:
        return "photometry.ellipse"

    @classmethod
    def layer1_keys(cls) -> list[str]:
        return ["band", "method", "level", "a", "e_a", "b", "e_b", "pa", "e_pa", "isophote", "e_isophote"]

    @classmethod
    def layer1_primary_keys(cls) -> list[str]:
        return ["record_id", "band", "method", "level", "isophote"]

    @classmethod
    def from_layer1(cls, data: dict[str, Any]) -> Self:
        return cls(
            band=data["band"],
            method=data["method"],
            level=float(data["level"]) if data.get("level") is not None else None,
            a=float(data["a"]) if data.get("a") is not None else None,
            e_a=float(data["e_a"]) if data.get("e_a") is not None else None,
            b=float(data["b"]) if data.get("b") is not None else None,
            e_b=float(data["e_b"]) if data.get("e_b") is not None else None,
            pa=float(data["pa"]) if data.get("pa") is not None else None,
            e_pa=float(data["e_pa"]) if data.get("e_pa") is not None else None,
            isophote=float(data["isophote"]) if data.get("isophote") is not None else None,
            e_isophote=float(data["e_isophote"]) if data.get("e_isophote") is not None else None,
        )

    @classmethod
    def layer2_table(cls) -> str:
        raise NotImplementedError

    @classmethod
    def layer2_keys(cls) -> list[str]:
        raise NotImplementedError

    def layer2_data(self) -> dict[str, Any]:
        raise NotImplementedError

    @classmethod
    def from_layer2(cls, data: dict[str, Any]) -> Self:
        raise NotImplementedError

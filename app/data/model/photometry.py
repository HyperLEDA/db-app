from typing import Any, Self, final

from app.data.model import interface


@final
class PhotometryCatalogObject(interface.CatalogObject):
    def __init__(
        self,
        band: str,
        mag: float,
        e_mag: float | None,
        method: str,
        **kwargs: Any,
    ) -> None:
        self.band = band
        self.mag = mag
        self.e_mag = e_mag
        self.method = method

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, PhotometryCatalogObject):
            return False
        return (
            self.band == value.band
            and self.mag == value.mag
            and self.e_mag == value.e_mag
            and self.method == value.method
        )

    def catalog(self) -> interface.RawCatalog:
        return interface.RawCatalog.PHOTOMETRY

    @classmethod
    def layer1_table(cls) -> str:
        return "photometry.data"

    @classmethod
    def layer1_keys(cls) -> list[str]:
        return ["band", "mag", "e_mag", "method"]

    @classmethod
    def layer1_primary_keys(cls) -> list[str]:
        return ["record_id", "method", "band"]

    @classmethod
    def from_layer1(cls, data: dict[str, Any]) -> Self:
        return cls(
            band=data["band"],
            mag=data["mag"],
            e_mag=data.get("e_mag"),
            method=data["method"],
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

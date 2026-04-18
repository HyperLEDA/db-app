from typing import Any, Self, final

from app.data.model import interface


@final
class PhotometryTotalCatalogObject(interface.CatalogObject):
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
        if not isinstance(value, PhotometryTotalCatalogObject):
            return False
        return (
            self.band == value.band
            and self.mag == value.mag
            and self.e_mag == value.e_mag
            and self.method == value.method
        )

    def catalog(self) -> interface.RawCatalog:
        return interface.RawCatalog.PHOTOMETRY__TOTAL

    @classmethod
    def layer1_table(cls) -> str:
        return "photometry.total"

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


@final
class PhotometryIsophotalCatalogObject(interface.CatalogObject):
    def __init__(
        self,
        band: str,
        isophote: float,
        mag: float,
        e_mag: float | None,
        **kwargs: Any,
    ) -> None:
        self.band = band
        self.isophote = isophote
        self.mag = mag
        self.e_mag = e_mag

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, PhotometryIsophotalCatalogObject):
            return False
        return (
            self.band == value.band
            and self.isophote == value.isophote
            and self.mag == value.mag
            and self.e_mag == value.e_mag
        )

    def catalog(self) -> interface.RawCatalog:
        return interface.RawCatalog.PHOTOMETRY__ISOPHOTAL

    @classmethod
    def layer1_table(cls) -> str:
        return "photometry.isophotal"

    @classmethod
    def layer1_keys(cls) -> list[str]:
        return ["band", "isophote", "mag", "e_mag"]

    @classmethod
    def layer1_primary_keys(cls) -> list[str]:
        return ["record_id", "band", "isophote"]

    @classmethod
    def from_layer1(cls, data: dict[str, Any]) -> Self:
        return cls(
            band=data["band"],
            isophote=float(data["isophote"]),
            mag=data["mag"],
            e_mag=data.get("e_mag"),
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

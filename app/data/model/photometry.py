from typing import Any, final

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
    def layer1_primary_keys(cls) -> list[str]:
        return ["record_id", "method", "band"]


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
    def layer1_primary_keys(cls) -> list[str]:
        return ["record_id", "band", "isophote"]

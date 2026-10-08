from typing import Any, Self, final, override

from app.catalogs import layer1
from app.catalogs.layer2 import interface


@final
class ICRSCatalogObject(interface.CatalogObject):
    def __init__(self, ra: float, dec: float, e_ra: float, e_dec: float) -> None:
        self.ra = ra
        self.dec = dec
        self.e_ra = e_ra
        self.e_dec = e_dec

    @classmethod
    @override
    def catalog(cls) -> interface.Catalog:
        return interface.Catalog.ICRS

    @classmethod
    @override
    def table(cls) -> str:
        return "layer2.icrs"

    @classmethod
    @override
    def sources(cls) -> list[layer1.Catalog]:
        return [layer1.Catalog.ICRS]

    @classmethod
    @override
    def keys(cls) -> list[str]:
        return ["ra", "e_ra", "dec", "e_dec"]

    @override
    def to_row(self) -> dict[str, Any]:
        return {
            "ra": self.ra,
            "dec": self.dec,
            "e_ra": self.e_ra,
            "e_dec": self.e_dec,
        }

    @classmethod
    @override
    def from_row(cls, data: dict[str, Any]) -> Self:
        return cls(ra=data["ra"], e_ra=data["e_ra"], dec=data["dec"], e_dec=data["e_dec"])

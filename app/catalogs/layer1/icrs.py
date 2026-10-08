from typing import Any, Self, final, override

from app.catalogs.layer1 import interface


@final
class ICRSCatalogObject(interface.CatalogObject):
    def __init__(
        self,
        ra: float,
        dec: float,
        e_ra: float,
        e_dec: float,
    ) -> None:
        self.ra = ra
        self.dec = dec
        self.e_ra = e_ra
        self.e_dec = e_dec

    @classmethod
    @override
    def catalog(cls) -> interface.Catalog:
        return interface.Catalog.ICRS

    @classmethod
    def title(cls) -> str:
        return "ICRS"

    @classmethod
    def description(cls) -> str:
        return "Equatorial coordinates in the ICRS frame."

    @classmethod
    def layer1_keys(cls) -> list[str]:
        return ["ra", "e_ra", "dec", "e_dec"]

    @classmethod
    def from_layer1(cls, data: dict[str, Any]) -> Self:
        return cls(ra=data["ra"], e_ra=data["e_ra"], dec=data["dec"], e_dec=data["e_dec"])

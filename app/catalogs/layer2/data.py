from typing import Any, Self, final, override

from app.catalogs.layer1 import Catalog as Layer1Catalog
from app.catalogs.layer2 import interface


@final
class DataCatalogObject(interface.CatalogObject):
    def __init__(
        self,
        design: str | None = None,
        ra: float | None = None,
        e_ra: float | None = None,
        dec: float | None = None,
        e_dec: float | None = None,
        type_name: str | None = None,
        bt: float | None = None,
        e_bt: float | None = None,
        d25: float | None = None,
        ba: float | None = None,
    ) -> None:
        self.design = design
        self.ra = ra
        self.e_ra = e_ra
        self.dec = dec
        self.e_dec = e_dec
        self.type_name = type_name
        self.bt = bt
        self.e_bt = e_bt
        self.d25 = d25
        self.ba = ba

    @classmethod
    @override
    def catalog(cls) -> interface.Catalog:
        return interface.Catalog.DATA

    @classmethod
    @override
    def table(cls) -> str:
        return "layer2.data"

    @classmethod
    @override
    def sources(cls) -> list[Layer1Catalog]:
        return [
            Layer1Catalog.DESIGNATION,
            Layer1Catalog.ICRS,
            Layer1Catalog.NATURE,
            Layer1Catalog.PHOTOMETRY__TOTAL,
            Layer1Catalog.GEOMETRY,
        ]

    @classmethod
    @override
    def keys(cls) -> list[str]:
        return ["design", "ra", "e_ra", "dec", "e_dec", "type_name", "bt", "e_bt", "d25", "ba"]

    @override
    def to_row(self) -> dict[str, Any]:
        return {
            "design": self.design,
            "ra": self.ra,
            "e_ra": self.e_ra,
            "dec": self.dec,
            "e_dec": self.e_dec,
            "type_name": self.type_name,
            "bt": self.bt,
            "e_bt": self.e_bt,
            "d25": self.d25,
            "ba": self.ba,
        }

    @classmethod
    @override
    def from_row(cls, data: dict[str, Any]) -> Self:
        return cls(
            design=data["design"],
            ra=data["ra"],
            e_ra=data["e_ra"],
            dec=data["dec"],
            e_dec=data["e_dec"],
            type_name=data["type_name"],
            bt=data["bt"],
            e_bt=data["e_bt"],
            d25=data["d25"],
            ba=data["ba"],
        )

from typing import Any, Self, final, override

from app.catalogs.layer1 import Catalog as Layer1Catalog
from app.catalogs.layer2 import interface


@final
class ObjectsCatalogObject(interface.CatalogObject):
    def __init__(
        self,
        name: str,
        objtype: str | None = None,
        ra: float | None = None,
        e_ra: float | None = None,
        dec: float | None = None,
        e_dec: float | None = None,
        galactic_l: float | None = None,
        galactic_b: float | None = None,
        sgl: float | None = None,
        sgb: float | None = None,
        ebv: float | None = None,
    ) -> None:
        self.name = name
        self.objtype = objtype
        self.ra = ra
        self.e_ra = e_ra
        self.dec = dec
        self.e_dec = e_dec
        self.l = galactic_l
        self.b = galactic_b
        self.sgl = sgl
        self.sgb = sgb
        self.ebv = ebv

    @classmethod
    @override
    def catalog(cls) -> interface.Catalog:
        return interface.Catalog.OBJECTS

    @classmethod
    @override
    def table(cls) -> str:
        return "layer2.objects"

    @classmethod
    @override
    def sources(cls) -> list[Layer1Catalog]:
        return [Layer1Catalog.DESIGNATION, Layer1Catalog.ICRS, Layer1Catalog.NATURE]

    @classmethod
    @override
    def keys(cls) -> list[str]:
        return ["name", "objtype", "ra", "e_ra", "dec", "e_dec", "l", "b", "sgl", "sgb", "ebv"]

    @override
    def to_row(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "objtype": self.objtype,
            "ra": self.ra,
            "e_ra": self.e_ra,
            "dec": self.dec,
            "e_dec": self.e_dec,
            "l": self.l,
            "b": self.b,
            "sgl": self.sgl,
            "sgb": self.sgb,
            "ebv": self.ebv,
        }

    @classmethod
    @override
    def from_row(cls, data: dict[str, Any]) -> Self:
        return cls(
            name=data["name"],
            objtype=data["objtype"],
            ra=_optional_float(data["ra"]),
            e_ra=_optional_float(data["e_ra"]),
            dec=_optional_float(data["dec"]),
            e_dec=_optional_float(data["e_dec"]),
            galactic_l=_optional_float(data["l"]),
            galactic_b=_optional_float(data["b"]),
            sgl=_optional_float(data["sgl"]),
            sgb=_optional_float(data["sgb"]),
            ebv=_optional_float(data["ebv"]),
        )


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)

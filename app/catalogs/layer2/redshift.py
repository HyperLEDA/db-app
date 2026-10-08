from typing import Any, Self, final, override

from app.catalogs import layer1
from app.catalogs.layer2 import interface


@final
class RedshiftCatalogObject(interface.CatalogObject):
    def __init__(self, cz: float, e_cz: float) -> None:
        self.cz = cz
        self.e_cz = e_cz

    @classmethod
    @override
    def catalog(cls) -> interface.Catalog:
        return interface.Catalog.REDSHIFT

    @classmethod
    @override
    def table(cls) -> str:
        return "layer2.cz"

    @classmethod
    @override
    def sources(cls) -> list[layer1.Catalog]:
        return [layer1.Catalog.REDSHIFT]

    @classmethod
    @override
    def keys(cls) -> list[str]:
        return ["cz", "e_cz"]

    @override
    def to_row(self) -> dict[str, Any]:
        return {"cz": self.cz, "e_cz": self.e_cz}

    @classmethod
    @override
    def from_row(cls, data: dict[str, Any]) -> Self:
        return cls(cz=data["cz"], e_cz=data["e_cz"])

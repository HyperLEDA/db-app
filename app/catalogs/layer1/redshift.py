from typing import Any, Self, final, override

from app.catalogs.layer1 import interface


@final
class RedshiftCatalogObject(interface.CatalogObject):
    def __init__(
        self,
        cz: float,
        e_cz: float,
    ) -> None:
        self.cz = cz
        self.e_cz = e_cz

    @classmethod
    @override
    def catalog(cls) -> interface.Catalog:
        return interface.Catalog.REDSHIFT

    @classmethod
    def title(cls) -> str:
        return "Redshift"

    @classmethod
    def description(cls) -> str:
        return "Heliocentric velocity (cz)."

    @classmethod
    def layer1_table(cls) -> str:
        return "cz.data"

    @classmethod
    def layer1_keys(cls) -> list[str]:
        return ["cz", "e_cz"]

    @classmethod
    def layer1_primary_keys(cls) -> list[str]:
        return ["record_id", "method"]

    @classmethod
    def from_layer1(cls, data: dict[str, Any]) -> Self:
        return cls(cz=data["cz"], e_cz=data["e_cz"])

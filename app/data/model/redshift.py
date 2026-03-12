from typing import Any, Self, final

from app.data.model import interface


@final
class RedshiftCatalogObject(interface.CatalogObject):
    def __init__(
        self,
        cz: float,
        e_cz: float,
    ) -> None:
        self.cz = cz
        self.e_cz = e_cz

    def layer0_data(self) -> dict[str, Any]:
        return {"cz": self.cz, "e_cz": self.e_cz}

    def catalog(self) -> interface.RawCatalog:
        return interface.RawCatalog.REDSHIFT

    @classmethod
    def layer1_table(cls) -> str:
        return "cz.data"

    @classmethod
    def layer1_keys(cls) -> list[str]:
        return ["cz", "e_cz"]

    def layer1_data(self) -> dict[str, Any]:
        return {"cz": self.cz, "e_cz": self.e_cz}

    @classmethod
    def from_layer1(cls, data: dict[str, Any]) -> Self:
        return cls(cz=data["cz"], e_cz=data["e_cz"])

    @classmethod
    def layer2_table(cls) -> str:
        return "layer2.cz"

    @classmethod
    def layer2_keys(cls) -> list[str]:
        return ["cz", "e_cz"]

    def layer2_data(self) -> dict[str, Any]:
        return {"cz": self.cz, "e_cz": self.e_cz}

    @classmethod
    def from_layer2(cls, data: dict[str, Any]) -> Self:
        return cls(cz=data["cz"], e_cz=data["e_cz"])

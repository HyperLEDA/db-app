from typing import Any, Self, final

from app.data.model import interface


@final
class RedshiftCatalogObject(interface.CatalogObject):
    def __init__(self, cz: float, e_cz: float, **kwargs) -> None:
        self.cz = cz
        self.e_cz = e_cz

    @classmethod
    def aggregate(cls, objects: list[Self]) -> Self:
        cz = sum(obj.cz for obj in objects) / len(objects)
        e_cz = sum(obj.e_cz for obj in objects) / len(objects)

        return cls(cz, e_cz)

    @classmethod
    def layer2_keys(cls) -> list[str]:
        return ["cz", "e_cz"]

    def catalog(self) -> interface.RawCatalog:
        return interface.RawCatalog.REDSHIFT

    def layer1_data(self) -> dict[str, Any]:
        return {
            "cz": self.cz,
            "e_cz": self.e_cz,
        }

    def layer2_data(self) -> dict[str, Any]:
        return {
            "cz": self.cz,
            "e_cz": self.e_cz,
        }

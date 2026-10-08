from typing import Any, Self, final, override

from app.catalogs.layer1 import interface


@final
class DesignationCatalogObject(interface.CatalogObject):
    def __init__(self, design: str, **kwargs) -> None:
        self.designation = design

    @classmethod
    @override
    def catalog(cls) -> interface.Catalog:
        return interface.Catalog.DESIGNATION

    @classmethod
    def title(cls) -> str:
        return "Designations"

    @classmethod
    def description(cls) -> str:
        return "Object designations."

    @classmethod
    def layer1_keys(cls) -> list[str]:
        return ["design"]

    @classmethod
    def layer1_primary_keys(cls) -> list[str]:
        return ["record_id", "design"]

    @classmethod
    def from_layer1(cls, data: dict[str, Any]) -> Self:
        return cls(design=data["design"])

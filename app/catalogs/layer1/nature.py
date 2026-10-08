from typing import Any, Self, final, override

from app.catalogs.layer1 import interface


@final
class NatureCatalogObject(interface.CatalogObject):
    def __init__(self, type_name: str, **kwargs: Any) -> None:
        self.type_name = type_name

    @classmethod
    @override
    def catalog(cls) -> interface.Catalog:
        return interface.Catalog.NATURE

    @classmethod
    def title(cls) -> str:
        return "Nature"

    @classmethod
    def description(cls) -> str:
        return "Object type classification."

    @classmethod
    def layer1_keys(cls) -> list[str]:
        return ["type_name"]

    @classmethod
    def from_layer1(cls, data: dict[str, Any]) -> Self:
        return cls(type_name=data["type_name"])

from typing import Any, Self, final, override

from app.data.model import interface


@final
class NatureCatalogObject(interface.CatalogObject):
    def __init__(self, type_name: str, **kwargs: Any) -> None:
        self.type_name = type_name

    @classmethod
    @override
    def catalog(cls) -> interface.RawCatalog:
        return interface.RawCatalog.NATURE

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

    @classmethod
    def layer2_table(cls) -> str:
        return "layer2.nature"

    @classmethod
    def layer2_keys(cls) -> list[str]:
        return ["type_name"]

    def layer2_data(self) -> dict[str, Any]:
        return {"type_name": self.type_name}

    @classmethod
    def from_layer2(cls, data: dict[str, Any]) -> Self:
        return cls(type_name=data["type_name"])

from typing import Any, Self, final

from app.data.model import interface


@final
class NatureCatalogObject(interface.CatalogObject):
    def __init__(self, type_name: str, **kwargs: Any) -> None:
        self.type_name = type_name

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, NatureCatalogObject):
            return False

        return self.type_name == value.type_name

    def layer0_data(self) -> dict[str, Any]:
        return {"type_name": self.type_name}

    def catalog(self) -> interface.RawCatalog:
        return interface.RawCatalog.NATURE

    @classmethod
    def layer1_table(cls) -> str:
        return "nature.data"

    @classmethod
    def layer1_keys(cls) -> list[str]:
        return ["type_name"]

    def layer1_data(self) -> dict[str, Any]:
        return {"type_name": self.type_name}

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

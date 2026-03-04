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

    @classmethod
    def from_custom(cls, type_name: Any) -> Self:
        return cls(str(type_name))

    def layer0_data(self) -> dict[str, Any]:
        return {"type_name": self.type_name}

    @classmethod
    def aggregate(cls, objects: list[Self]) -> Self:
        type_counts: dict[str, int] = {}
        for obj in objects:
            type_counts[obj.type_name] = type_counts.get(obj.type_name, 0) + 1

        max_type = ""
        for name, count in type_counts.items():
            if count > type_counts.get(max_type, 0):
                max_type = name

        return cls(max_type)

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

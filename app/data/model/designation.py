from typing import Any, Self, final

from app.data.model import interface


@final
class DesignationCatalogObject(interface.CatalogObject):
    def __init__(self, design: str, **kwargs) -> None:
        self.designation = design

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, DesignationCatalogObject):
            return False

        return self.designation == value.designation

    @classmethod
    def aggregate(cls, objects: list[Self]) -> Self:
        """
        Aggregate designation is selected as the most common designation among all objects.
        """
        name_counts = {}

        for obj in objects:
            name_counts[obj.designation] = name_counts.get(obj.designation, 0) + 1

        max_name = ""

        for name, count in name_counts.items():
            if count > name_counts.get(max_name, 0):
                max_name = name

        return cls(max_name)

    def catalog(self) -> interface.RawCatalog:
        return interface.RawCatalog.DESIGNATION

    @classmethod
    def layer2_keys(cls) -> list[str]:
        return ["design"]

    def layer1_data(self) -> dict[str, Any]:
        return {
            "design": self.designation,
        }

    def layer2_data(self) -> dict[str, Any]:
        return {
            "design": self.designation,
        }

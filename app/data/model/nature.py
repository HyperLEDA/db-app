import statistics
from typing import Any, Self, final

from app.data.model import errors, interface
from app.lib.storage import enums

# all options are lowercase since we will .lower() everything anyway
options = {
    enums.Nature.STAR: ["*", "s", "star"],
    enums.Nature.STAR_SYSTEM: ["*s", "**", "stars", "c", "s2", "s3", "a", "s+", "gc", "oc"],
    enums.Nature.INTERSTELLAR_MEDIUM: ["ism"],
    enums.Nature.GALAXY: ["g", "gal", "galaxy"],
    enums.Nature.MULTIPLE_GALAXIES: ["mg", "m2", "m3", "mc"],
    enums.Nature.OTHER: ["o"],
    enums.Nature.ERROR: ["!", "e", "x", "pg", "u"],
}

option_to_nature: dict[str, enums.Nature] = {}
for nature, names in options.items():
    for name in names:
        option_to_nature[name] = nature


@final
class NatureCatalogObject(interface.CatalogObject):
    def __init__(self, nature: enums.Nature) -> None:
        self.nature = nature

    @classmethod
    def from_custom(cls, nature: str) -> Self:
        if (n := nature.lower()) in option_to_nature:
            return cls(option_to_nature[n])

        raise errors.CatalogObjectCreationError(f"Unknown object type: {nature}")

    @classmethod
    def aggregate(cls, objects: list[Self]) -> Self:
        return cls(statistics.mode([obj.nature for obj in objects]))

    @classmethod
    def catalog(cls) -> interface.RawCatalog:
        return interface.RawCatalog.NATURE

    @classmethod
    def layer1_table(cls) -> str:
        return "nature.data"

    @classmethod
    def layer1_keys(cls) -> list[str]:
        return ["nature"]

    def layer1_data(self) -> dict[str, Any]:
        return {"nature": self.nature}

    @classmethod
    def from_layer1(cls, data: dict[str, Any]) -> Self:
        return cls(nature=data["nature"])

    @classmethod
    def layer2_table(cls) -> str:
        return "layer2.nature"

    @classmethod
    def layer2_keys(cls) -> list[str]:
        return ["nature"]

    def layer2_data(self) -> dict[str, Any]:
        return {"nature": self.nature}

    @classmethod
    def from_layer2(cls, data: dict[str, Any]) -> Self:
        return cls(nature=data["nature"])

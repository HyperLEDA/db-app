from typing import Any, Self, final

from app.data.model import interface


@final
class NoteCatalogObject(interface.CatalogObject):
    def __init__(self, note: str, **kwargs: Any) -> None:
        self.note = note

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, NoteCatalogObject):
            return False

        return self.note == value.note

    def catalog(self) -> interface.RawCatalog:
        return interface.RawCatalog.NOTE

    @classmethod
    def layer1_table(cls) -> str:
        return "note.data"

    @classmethod
    def layer1_keys(cls) -> list[str]:
        return ["note"]

    @classmethod
    def from_layer1(cls, data: dict[str, Any]) -> Self:
        return cls(note=data["note"])

    @classmethod
    def layer2_table(cls) -> str:
        raise NotImplementedError

    @classmethod
    def layer2_keys(cls) -> list[str]:
        raise NotImplementedError

    def layer2_data(self) -> dict[str, Any]:
        raise NotImplementedError

    @classmethod
    def from_layer2(cls, data: dict[str, Any]) -> Self:
        raise NotImplementedError

from typing import final

from app.data.model import interface


@final
class NoteCatalogObject(interface.CatalogObject):
    def catalog(self) -> interface.RawCatalog:
        return interface.RawCatalog.NOTE

    @classmethod
    def title(cls) -> str:
        return "Note"

    @classmethod
    def description(cls) -> str:
        return "Free-text notes attached to records."

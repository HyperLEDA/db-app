from typing import final, override

from app.catalogs import interface


@final
class NoteCatalogObject(interface.CatalogObject):
    @classmethod
    @override
    def catalog(cls) -> interface.RawCatalog:
        return interface.RawCatalog.NOTE

    @classmethod
    def title(cls) -> str:
        return "Note"

    @classmethod
    def description(cls) -> str:
        return "Free-text notes attached to records."

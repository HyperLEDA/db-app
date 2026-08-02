from typing import final

from app.data.model import interface


@final
class NoteCatalogObject(interface.CatalogObject):
    def catalog(self) -> interface.RawCatalog:
        return interface.RawCatalog.NOTE

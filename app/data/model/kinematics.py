from typing import Any, final

from app.data.model import interface


@final
class KinematicsLineWidthCatalogObject(interface.CatalogObject):
    def __init__(
        self,
        line_id: str,
        width: float,
        resolution: float,
        e_width: float | None = None,
        method: str = "peak",
        level: float = 50,
        quality: str = "regular",
        **kwargs: Any,
    ) -> None:
        self.line_id = line_id
        self.width = width
        self.e_width = e_width
        self.method = method
        self.level = level
        self.resolution = resolution
        self.quality = quality

    def catalog(self) -> interface.RawCatalog:
        return interface.RawCatalog.KINEMATICS__LINE_WIDTH

    @classmethod
    def title(cls) -> str:
        return "Kinematics (line width)"

    @classmethod
    def description(cls) -> str:
        return "Spectral line width measurements."

    @classmethod
    def layer1_table(cls) -> str:
        return "kinematics.line_width"

    @classmethod
    def layer1_primary_keys(cls) -> list[str]:
        return ["record_id", "line_id", "method", "level"]

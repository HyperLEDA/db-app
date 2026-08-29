from typing import Any, final, override

from app.data.model import interface


@final
class SpectroscopyIntegratedFluxDensityCatalogObject(interface.CatalogObject):
    def __init__(
        self,
        line_id: str,
        flux: float,
        e_flux: float | None = None,
        method: str = "sum",
        quality: str = "regular",
        **kwargs: Any,
    ) -> None:
        self.line_id = line_id
        self.flux = flux
        self.e_flux = e_flux
        self.method = method
        self.quality = quality

    @classmethod
    @override
    def catalog(cls) -> interface.RawCatalog:
        return interface.RawCatalog.SPECTROSCOPY__INTEGRATED_FLUX_DENSITY

    @classmethod
    def title(cls) -> str:
        return "Spectroscopy (integrated flux density)"

    @classmethod
    def description(cls) -> str:
        return "Integrated spectral line flux densities."

    @classmethod
    def layer1_table(cls) -> str:
        return "spectroscopy.integrated_flux_density"

    @classmethod
    def layer1_primary_keys(cls) -> list[str]:
        return ["record_id", "line_id", "method"]


@final
class SpectroscopyEnergyFluxCatalogObject(interface.CatalogObject):
    def __init__(
        self,
        line_id: str,
        flux: float,
        e_flux: float | None = None,
        quality: str = "regular",
        **kwargs: Any,
    ) -> None:
        self.line_id = line_id
        self.flux = flux
        self.e_flux = e_flux
        self.quality = quality

    @classmethod
    @override
    def catalog(cls) -> interface.RawCatalog:
        return interface.RawCatalog.SPECTROSCOPY__ENERGY_FLUX

    @classmethod
    def title(cls) -> str:
        return "Spectroscopy (energy flux)"

    @classmethod
    def description(cls) -> str:
        return "Spectral line energy fluxes."

    @classmethod
    def layer1_table(cls) -> str:
        return "spectroscopy.energy_flux"

    @classmethod
    def layer1_primary_keys(cls) -> list[str]:
        return ["record_id", "line_id"]

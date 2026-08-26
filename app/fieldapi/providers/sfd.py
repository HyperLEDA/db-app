import pathlib
from collections.abc import Callable

import dustmaps.config
import dustmaps.sfd as dustmaps_sfd
import numpy as np
from astropy import coordinates as astro_coords
from astropy import units as u

from app.fieldapi.presentation import interface
from app.fieldapi.providers import interface as provider_interface

SFDQueryFn = Callable[[astro_coords.SkyCoord], np.ndarray]

SFD_MAP_DIR = "sfd"
SFD_FILES = ("SFD_dust_4096_ngp.fits", "SFD_dust_4096_sgp.fits")


def sfd_files_present(map_dir: pathlib.Path) -> bool:
    return all((map_dir / name).is_file() for name in SFD_FILES)


class SFDProvider(provider_interface.DatasetProvider):
    def __init__(self, query: SFDQueryFn | None = None) -> None:
        self._query: SFDQueryFn | None = query

    def metadata(self, dataset_id: str, name: str, version: str) -> interface.DatasetInfo:
        return interface.DatasetInfo(
            id=dataset_id,
            name=name,
            version=version,
            dimensions=2,
            quantity="ebv",
            unit="mag",
            description="Galactic dust reddening map",
            citation="Schlegel, Finkbeiner & Davis 1998",
        )

    def prepare(self, data_dir: pathlib.Path) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        dustmaps.config.config["data_dir"] = str(data_dir)
        map_dir = data_dir / SFD_MAP_DIR
        if not sfd_files_present(map_dir):
            dustmaps_sfd.fetch()
        if self._query is None:
            self._query = dustmaps_sfd.SFDQuery(map_dir=str(map_dir))

    def sample(self, coordinates: list[interface.SkyCoordinate]) -> list[float]:
        if self._query is None:
            raise RuntimeError("SFD provider is not prepared")

        skycoords = astro_coords.SkyCoord(
            [coordinate.ra_deg for coordinate in coordinates] * u.Unit("deg"),
            [coordinate.dec_deg for coordinate in coordinates] * u.Unit("deg"),
            frame="icrs",
        )
        values = np.atleast_1d(self._query(skycoords))
        return [float(value) for value in values]

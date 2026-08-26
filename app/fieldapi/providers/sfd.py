import pathlib
from collections.abc import Callable

import dustmaps.config
import dustmaps.sfd as dustmaps_sfd
import numpy as np
from astropy import coordinates as astro_coords
from astropy import units as u

from app.fieldapi import config as fieldapi_config
from app.fieldapi.presentation import interface
from app.fieldapi.providers import interface as provider_interface

SFDQueryFn = Callable[[astro_coords.SkyCoord], np.ndarray]


def map_files_present(map_dir: pathlib.Path, files: list[str]) -> bool:
    return all((map_dir / name).is_file() for name in files)


def missing_files(map_dir: pathlib.Path, files: list[str]) -> list[str]:
    return [name for name in files if not (map_dir / name).is_file()]


class SFDProvider(provider_interface.DatasetProvider):
    def __init__(self, dataset: fieldapi_config.DatasetConfig, query: SFDQueryFn | None = None) -> None:
        self.dataset = dataset
        self._query: SFDQueryFn | None = query

    def prepare(self, data_dir: pathlib.Path) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        dustmaps.config.config["data_dir"] = str(data_dir)
        map_dir = data_dir / self.dataset.storage.dir
        if not map_files_present(map_dir, self.dataset.storage.files):
            dustmaps_sfd.fetch()
        missing = missing_files(map_dir, self.dataset.storage.files)
        if missing:
            raise FileNotFoundError(
                f"Missing dataset files for {self.dataset.id} in {map_dir}: {', '.join(missing)}"
            )
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

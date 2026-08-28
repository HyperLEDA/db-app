import pathlib
from collections.abc import Callable

import dustmaps.sfd as dustmaps_sfd
import numpy as np
import requests
from astropy import coordinates as astro_coords
from astropy import units as u

from app.fieldapi import config as fieldapi_config
from app.fieldapi.providers import interface as provider_interface
from app.specs import fieldapi

SFDQueryFn = Callable[[astro_coords.SkyCoord], np.ndarray]
SFD_BASE_URL = "https://portal.nersc.gov/project/cosmo/data/dust/v0_0/maps"


def map_files_present(map_dir: pathlib.Path, files: list[str]) -> bool:
    return all((map_dir / name).is_file() for name in files)


def missing_files(map_dir: pathlib.Path, files: list[str]) -> list[str]:
    return [name for name in files if not (map_dir / name).is_file()]


def download_sfd_files(map_dir: pathlib.Path, files: list[str]) -> None:
    map_dir.mkdir(parents=True, exist_ok=True)
    for name in files:
        dest = map_dir / name
        url = f"{SFD_BASE_URL}/{name}"
        with requests.get(url, stream=True, timeout=60) as response:
            response.raise_for_status()
            with dest.open("wb") as file:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        file.write(chunk)


class SFDProvider(provider_interface.DatasetProvider):
    def __init__(self, dataset: fieldapi_config.DatasetConfig, query: SFDQueryFn | None = None) -> None:
        self.dataset = dataset
        self._query: SFDQueryFn | None = query

    def prepare(self, data_dir: pathlib.Path) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        map_dir = data_dir / self.dataset.storage.dir
        files = self.dataset.storage.files

        missing = missing_files(map_dir, files)
        if missing:
            download_sfd_files(map_dir, missing)
            still_missing = missing_files(map_dir, files)
            if still_missing:
                raise FileNotFoundError(
                    f"Missing dataset files for {self.dataset.id} in {map_dir}: {', '.join(still_missing)}"
                )

        if self._query is None:
            try:
                self._query = dustmaps_sfd.SFDQuery(map_dir=str(map_dir))
            except (OSError, TypeError, ValueError):
                download_sfd_files(map_dir, files)
                self._query = dustmaps_sfd.SFDQuery(map_dir=str(map_dir))

    def sample(self, coordinates: list[fieldapi.SkyCoordinate]) -> list[float]:
        if self._query is None:
            raise RuntimeError("SFD provider is not prepared")

        skycoords = astro_coords.SkyCoord(
            [coordinate.ra_deg for coordinate in coordinates] * u.Unit("deg"),
            [coordinate.dec_deg for coordinate in coordinates] * u.Unit("deg"),
            frame="icrs",
        )
        values = np.atleast_1d(self._query(skycoords))
        return [float(value) for value in values]

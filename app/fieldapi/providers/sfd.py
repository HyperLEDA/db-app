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

        values: list[float | None] = [None] * len(coordinates)
        by_frame: dict[interface.CoordinateFrame, list[tuple[int, interface.SkyCoordinate]]] = {}
        for index, coordinate in enumerate(coordinates):
            by_frame.setdefault(coordinate.frame, []).append((index, coordinate))

        query = self._query
        for frame, indexed_coordinates in by_frame.items():
            skycoords = astro_coords.SkyCoord(
                [coordinate.longitude_deg for _, coordinate in indexed_coordinates] * u.Unit("deg"),
                [coordinate.latitude_deg for _, coordinate in indexed_coordinates] * u.Unit("deg"),
                frame=frame.value,
            )
            frame_values = np.atleast_1d(query(skycoords))
            for (index, _), value in zip(indexed_coordinates, frame_values, strict=True):
                values[index] = float(value)

        result: list[float] = []
        for value in values:
            if value is None:
                raise RuntimeError("missing sampled value")
            result.append(value)
        return result

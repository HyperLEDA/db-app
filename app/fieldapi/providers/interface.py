import abc
import pathlib

from app.fieldapi.presentation import interface


class DatasetProvider(abc.ABC):
    @abc.abstractmethod
    def metadata(self, dataset_id: str, name: str, version: str) -> interface.DatasetInfo:
        pass

    @abc.abstractmethod
    def prepare(self, data_dir: pathlib.Path) -> None:
        pass

    @abc.abstractmethod
    def sample(self, coordinates: list[interface.SkyCoordinate]) -> list[float]:
        pass

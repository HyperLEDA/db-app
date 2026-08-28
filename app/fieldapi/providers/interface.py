import abc
import pathlib

from app.specs import fieldapi


class DatasetProvider(abc.ABC):
    @abc.abstractmethod
    def prepare(self, data_dir: pathlib.Path) -> None:
        pass

    @abc.abstractmethod
    def sample(self, coordinates: list[fieldapi.SkyCoordinate]) -> list[float]:
        pass

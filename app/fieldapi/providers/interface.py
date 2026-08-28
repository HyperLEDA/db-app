import abc
import pathlib

from app.specs import fieldapi as spec


class DatasetProvider(abc.ABC):
    @abc.abstractmethod
    def prepare(self, data_dir: pathlib.Path) -> None:
        pass

    @abc.abstractmethod
    def sample(self, coordinates: list[spec.SkyCoordinate]) -> list[float]:
        pass

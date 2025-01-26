import datetime
from typing import final

from app.data import repositories
from app.domain.importers import interface


@final
class DesignationImporter(interface.Importer):
    def __init__(self, layer1_repo: repositories.Layer1Repository) -> None:
        self.layer1_repo = layer1_repo

    def collect(self, dt: datetime.datetime) -> dict[interface.pgc, interface.UnaggregatedInfo]:
        raise NotImplementedError

    def aggregate(self, unaggregated_info: interface.UnaggregatedInfo) -> interface.ObjectInfo:
        raise NotImplementedError

    def write(self, objects: dict[interface.pgc, interface.ObjectInfo]) -> None:
        raise NotImplementedError

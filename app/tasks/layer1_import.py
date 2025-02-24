from typing import final

from app.tasks import interface


@final
class Layer1Import(interface.Task):
    def __init__(self, config_path: str, table_id: int, batch_size: int) -> None:
        self.config_path = config_path
        self.table_id = table_id
        self.batch_size = batch_size

    @classmethod
    def name(cls):
        return "layer1-import"

    def prepare(self, config: interface.Config):
        raise NotImplementedError

    def run(self):
        raise NotImplementedError

    def cleanup(self):
        raise NotImplementedError

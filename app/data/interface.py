import abc

from app.data import model


class Repository(abc.ABC):
    def create_bibliography(self, bibliography: model.Bibliography):
        raise NotImplementedError()

    def get_bibliography(self, id: int) -> model.Bibliography:
        raise NotImplementedError()

    def get_bibliography_list(self, offset: int, limit: int) -> list[model.Bibliography]:
        raise NotImplementedError()

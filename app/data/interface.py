import abc

from app.data import model


class Repository(abc.ABC):
    def create_bibliography(self, bibliography: model.Bibliography):
        raise NotImplementedError()

    def get_bibliography(self) -> model.Bibliography:
        raise NotImplementedError()

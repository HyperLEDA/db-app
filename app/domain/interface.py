import abc

from app.domain import model


class Actions(abc.ABC):
    def create_source(self, r: model.CreateSourceRequest) -> model.CreateSourceResponse:
        raise NotImplementedError()

    def get_source(self, r: model.GetSourceRequest) -> model.GetSourceResponse:
        raise NotImplementedError()

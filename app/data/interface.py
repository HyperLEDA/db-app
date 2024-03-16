import abc

from app.data import model


class Repository(abc.ABC):
    def create_bibliography(self, bibliography: model.Bibliography):
        raise NotImplementedError("not implemented")

    def get_bibliography(self, id: int) -> model.Bibliography:
        raise NotImplementedError("not implemented")

    def get_bibliography_list(self, offset: int, limit: int) -> list[model.Bibliography]:
        raise NotImplementedError("not implemented")

    def create_objects(self, n: int) -> list[int]:
        raise NotImplementedError("not implemented")

    def create_designations(self, designations: list[model.Designation]):
        raise NotImplementedError("not implemented")

    def get_designations(self, pgc: int, offset: int, limit: int) -> list[model.Designation]:
        raise NotImplementedError("not implemented")

    def create_coordinates(self, coordinates: list[model.CoordinateData]):
        raise NotImplementedError("not implemented")

import abc
from typing import Literal

import pydantic


class SkyCoordinate(pydantic.BaseModel):
    ra_deg: float = pydantic.Field(ge=0, lt=360)
    dec_deg: float = pydantic.Field(ge=-90, le=90)


class DatasetInfo(pydantic.BaseModel):
    id: str
    name: str
    version: str
    dimensions: Literal[2]
    quantity: str
    unit: str
    description: str
    citation: str


class ListDatasetsResponse(pydantic.BaseModel):
    datasets: list[DatasetInfo]


class SampleRequest(pydantic.BaseModel):
    dataset: str
    coordinates: list[SkyCoordinate] = pydantic.Field(min_length=1, max_length=10_000)


class SampleResponse(pydantic.BaseModel):
    values: list[float]


class Actions(abc.ABC):
    @abc.abstractmethod
    def list_datasets(self) -> ListDatasetsResponse:
        pass

    @abc.abstractmethod
    def sample(self, request: SampleRequest) -> SampleResponse:
        pass

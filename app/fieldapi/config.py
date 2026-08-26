import pathlib

import pydantic


class DatasetConfig(pydantic.BaseModel):
    id: str
    provider: str
    name: str
    version: str


class DatasetsConfig(pydantic.BaseModel):
    data_dir: pathlib.Path
    enabled: list[DatasetConfig]

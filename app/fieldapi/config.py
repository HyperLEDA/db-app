import pathlib
from typing import Literal

import pydantic

from app.fieldapi.presentation import interface


class DatasetStorageConfig(pydantic.BaseModel):
    dir: str
    files: list[str] = pydantic.Field(min_length=1)


class DatasetConfig(pydantic.BaseModel):
    id: str
    provider: str
    name: str
    version: str
    dimensions: Literal[2] = 2
    quantity: str
    unit: str
    description: str
    bibcode: str
    storage: DatasetStorageConfig

    def to_dataset_info(self) -> interface.DatasetInfo:
        return interface.DatasetInfo(
            id=self.id,
            name=self.name,
            version=self.version,
            dimensions=self.dimensions,
            quantity=self.quantity,
            unit=self.unit,
            description=self.description,
            bibcode=self.bibcode,
        )


class DatasetsConfig(pydantic.BaseModel):
    data_dir: pathlib.Path
    enabled: list[DatasetConfig]

    @pydantic.model_validator(mode="after")
    def validate_unique_dataset_ids(self) -> "DatasetsConfig":
        ids = [dataset.id for dataset in self.enabled]
        duplicates = {dataset_id for dataset_id in ids if ids.count(dataset_id) > 1}
        if duplicates:
            raise ValueError(f"Duplicate dataset ids: {', '.join(sorted(duplicates))}")
        return self

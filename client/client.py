import dataclasses
from typing import Any

import pandas
import requests

from . import config, error
from .gen import model


class HyperLedaClient:
    """
    This is client for HyperLeda service. It allows one to query different types of data from the database
    and, if authentication information is present, add new data.
    """

    # TODO: credentials
    def __init__(self, endpoint: str = config.DEFAULT_ENDPOINT) -> None:
        self.endpoint = endpoint

    def _post(self, path: str, request: Any) -> dict[str, Any]:
        response = requests.post(f"{self.endpoint}{path}", json=dataclasses.asdict(request))

        if not response.ok:
            raise error.APIError.from_dict(response.json())

        return response.json()

    def _get(self, path: str, query: dict[str, str]) -> dict[str, Any]:
        response = requests.get(f"{self.endpoint}{path}", params=query)

        if not response.ok:
            raise error.APIError.from_dict(response.json())

        return response.json()

    def create_bibliography(self, bibcode: str, title: str, authors: list[str], year: int) -> int:
        """
        Create new bibliography entry in the database. For now one must enter both bibcode and
        other metadata about the article in order for it co be created correctly. In future integration
        with NASA ADS is planned which will remove necessity for separate title, author and year specification.
        """
        data = self._post(
            "/api/v1/admin/source",
            model.CreateSourceRequestSchema(bibcode=bibcode, title=title, authors=authors, year=year),
        )

        return model.CreateSourceResponseSchema(**data["data"]).id

    def get_bibliography(self, bibliography_id: int) -> model.GetSourceResponseSchema:
        data = self._get("/api/v1/source", {"id": bibliography_id})

        return model.GetSourceResponseSchema(**data["data"])

    def create_table(self, table_description: model.CreateTableRequestSchema) -> int:
        data = self._post(
            "/api/v1/admin/table",
            table_description,
        )

        return model.CreateTableResponseSchema(**data["data"]).id

    def add_data(self, table_id: int, data: pandas.DataFrame) -> None:
        _ = self._post(
            "/api/v1/admin/table/data",
            model.AddDataRequestSchema(table_id, data.to_dict("records")),
        )

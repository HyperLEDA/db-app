import dataclasses

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

    def create_bibliography(self, bibcode: str, title: str, authors: list[str], year: int) -> int:
        """
        Create new bibliography entry in the database. For now one must enter both bibcode and
        other metadata about the article in order for it co be created correctly. In future integration
        with NASA ADS is planned which will remove necessity for separate title, author and year specification.
        """
        response = requests.post(
            f"{self.endpoint}/api/v1/admin/source",
            json=dataclasses.asdict(
                model.CreateSourceRequestSchema(
                    bibcode=bibcode,
                    title=title,
                    authors=authors,
                    year=year,
                )
            ),
        )

        if not response.ok:
            raise error.APIError.from_dict(response.json())

        data = response.json()

        return int(data["data"]["id"])

    def get_bibliography(self, bibliography_id: int) -> model.GetSourceResponseSchema:
        response = requests.get(f"{self.endpoint}/api/v1/source?id={bibliography_id}")

        if not response.ok:
            raise error.APIError.from_dict(response.json())

        data = response.json()

        return model.GetSourceResponseSchema(**data["data"])

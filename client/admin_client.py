import config
import error
import requests


class HyperLedaAdminClient:
    """
    This is administrative client. It uses /api/v1/admin handlers and requires you to have credentails to
    create objects in HyperLeda database.
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
            json={
                "bibcode": bibcode,
                "title": title,
                "authors": authors,
                "year": year,
            },
        )

        if not response.ok:
            raise error.APIError.from_dict(response.json())

        data = response.json()

        return int(data["id"])

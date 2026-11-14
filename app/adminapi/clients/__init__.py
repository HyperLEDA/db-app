from unittest import mock

from astroquery import nasa_ads as ads
from astroquery import vizier

from app.adminapi.clients.prefect import PrefectClient

__all__ = [
    "Clients",
    "PrefectClient",
    "get_mock_clients",
]


class Clients:
    def __init__(self, ads_token: str, prefect_api_url: str) -> None:
        self.ads = ads.ADSClass()
        self.ads.TOKEN = ads_token
        self.ads.ADS_FIELDS = ["bibcode", "title", "author", "pubdate"]

        self.vizier = vizier.VizierClass()
        self.vizier.TIMEOUT = 30

        self.prefect = PrefectClient(prefect_api_url)


def get_mock_clients() -> Clients:
    c = Clients(ads_token="test", prefect_api_url="http://localhost:4200/api")
    c.ads = mock.MagicMock()
    c.vizier = mock.MagicMock()
    c.prefect = mock.MagicMock()
    return c

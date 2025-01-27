from unittest import mock

from astroquery import nasa_ads as ads
from astroquery import vizier


class Clients:
    """Stores clients for network interactions"""

    def __init__(self, ads_token: str) -> None:
        self.ads = ads.ADSClass()
        self.ads.TOKEN = ads_token
        self.ads.ADS_FIELDS = ["bibcode", "title", "author", "pubdate"]

        self.vizier = vizier.VizierClass()
        self.vizier.TIMEOUT = 30


def get_mock_clients() -> Clients:
    c = Clients(ads_token="test")
    c.ads = mock.MagicMock()
    c.vizier = mock.MagicMock()

    return c

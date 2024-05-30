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

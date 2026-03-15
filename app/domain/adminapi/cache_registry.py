from app.data.model import RawdataTableRowCounts
from app.lib.cache.cache import BackgroundCache


class CacheRegistry:
    def __init__(
        self,
        rawdata_row_counts: BackgroundCache[RawdataTableRowCounts],
    ) -> None:
        self.rawdata_row_counts = rawdata_row_counts

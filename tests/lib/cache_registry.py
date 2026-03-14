from datetime import timedelta
from unittest import mock

from app.data import model
from app.domain.adminapi import CacheRegistry
from app.lib.cache import BackgroundCache


def get_mock_cache_registry() -> CacheRegistry:
    cache = mock.MagicMock()
    cache.get.return_value = model.RawdataTableRowCounts(rows_by_table={})
    return CacheRegistry(rawdata_row_counts=cache)


def get_cache_registry(layer0_repo):
    def refresh():
        names = layer0_repo.list_tables()
        return model.RawdataTableRowCounts(rows_by_table={name: layer0_repo.total_rows(name) for name in names})

    rawdata_row_counts = BackgroundCache(
        name="rawdata_table_row_counts",
        refresh_func=refresh,
        refresh_frequency=timedelta(minutes=1),
        refresh_timeout=timedelta(seconds=30),
    )
    return CacheRegistry(rawdata_row_counts=rawdata_row_counts)

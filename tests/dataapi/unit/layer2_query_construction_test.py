import re

import pytest

from app import catalogs
from app.dataapi import repository
from app.lib import mock


@pytest.fixture
def repo() -> tuple[mock.Mock, repository.Repository]:
    storage = mock.Mock()
    storage.query.return_value = []
    return storage, repository.Repository(storage, mock.Mock())


def _one_to_one_query_for(
    repo_fixture: tuple[mock.Mock, repository.Repository],
    raw_catalogs: list[catalogs.RawCatalog],
) -> str:
    storage, repo = repo_fixture
    repo.query_catalogs(raw_catalogs, [1, 2])
    queries = [call.args[0] for call in storage.query.call_args_list]
    join_queries = [q for q in queries if "unnest" in q]
    assert len(join_queries) == 1
    return re.sub(r"\s+", " ", join_queries[0]).strip()


def test_one_to_one_uses_unnest_left_join(repo: tuple[mock.Mock, repository.Repository]) -> None:
    query = _one_to_one_query_for(
        repo,
        [catalogs.RawCatalog.DESIGNATION, catalogs.RawCatalog.ICRS, catalogs.RawCatalog.REDSHIFT],
    )

    assert "unnest(%s::int[]) WITH ORDINALITY" in query
    assert "LEFT JOIN layer2.designation USING (pgc)" in query
    assert "LEFT JOIN layer2.icrs USING (pgc)" in query
    assert "LEFT JOIN layer2.cz USING (pgc)" in query
    assert "FULL JOIN" not in query
    assert "search_params" not in query


def test_one_to_many_catalogs_use_separate_queries(repo: tuple[mock.Mock, repository.Repository]) -> None:
    _, repo_instance = repo
    repo_instance.query_catalogs(
        [catalogs.RawCatalog.PHOTOMETRY__TOTAL, catalogs.RawCatalog.NOTE],
        [1],
    )
    storage, _ = repo
    queries = [call.args[0] for call in storage.query.call_args_list]
    assert any("layer2.photometry_total" in q for q in queries)
    assert any("layer2.notes" in q for q in queries)
    assert not any("unnest" in q for q in queries)


def test_mixed_catalogs_join_only_one_to_one(repo: tuple[mock.Mock, repository.Repository]) -> None:
    storage, repo_instance = repo
    repo_instance.query_catalogs(
        [catalogs.RawCatalog.ICRS, catalogs.RawCatalog.PHOTOMETRY__TOTAL],
        [1],
    )
    queries = [call.args[0] for call in storage.query.call_args_list]
    join_queries = [q for q in queries if "unnest" in q]
    assert len(join_queries) == 1
    query = re.sub(r"\s+", " ", join_queries[0]).strip()
    assert "LEFT JOIN layer2.icrs USING (pgc)" in query
    assert "photometry_total" not in query
    assert any("layer2.photometry_total" in q for q in queries)

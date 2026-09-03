import pytest
import structlog

from app.adminapi import domain, repository
from app.lib.web.errors import ConflictError, NotFoundError, RuleValidationError
from app.specs import adminapi
from tests.lib.postgres import PostgresTestStorage

pytestmark = pytest.mark.usefixtures("cleared_pg_storage")


@pytest.fixture(scope="module")
def manager(pg_storage: PostgresTestStorage) -> domain.ReferencesManager:
    repo = repository.Repository(pg_storage.get_storage(), structlog.get_logger())
    return domain.ReferencesManager(repo)


@pytest.fixture(scope="module")
def repo(pg_storage: PostgresTestStorage) -> repository.Repository:
    return repository.Repository(pg_storage.get_storage(), structlog.get_logger())


def test_create_and_list_distance_method(manager: domain.ReferencesManager) -> None:
    manager.create_row(
        "distance",
        "methods",
        adminapi.CreateReferenceRowRequest(
            row={
                "id": "TRGB",
                "indicator": "standard candle",
                "title": "Tip of the red giant branch",
                "description": "Resolved stellar population distance indicator",
            },
        ),
    )

    rows = manager.list_rows(
        "distance",
        "methods",
        adminapi.ListReferenceRowsRequest(query="TRGB"),
    )
    assert rows.total == 1
    assert rows.items[0].key == {"id": "TRGB"}
    assert rows.items[0].row["title"] == "Tip of the red giant branch"


def test_create_bib_and_calibration_with_reference_options(
    manager: domain.ReferencesManager,
    repo: repository.Repository,
) -> None:
    bib_id = repo.create_bibliography(
        "2019ApJ...887...80F",
        2019,
        ["Freedman W. L."],
        "The Carnegie-Chicago Hubble Program",
    )
    manager.create_row(
        "distance",
        "methods",
        adminapi.CreateReferenceRowRequest(
            row={
                "id": "TRGB",
                "title": "TRGB",
            },
        ),
    )
    manager.create_row(
        "distance",
        "calibrations",
        adminapi.CreateReferenceRowRequest(
            row={
                "id": "TRGB/F19",
                "method_id": "TRGB",
                "bib": bib_id,
                "specification": "Freedman+2019",
            },
        ),
    )

    options = manager.list_field_options(
        "distance",
        "calibrations",
        "bib",
        adminapi.ListReferenceFieldOptionsRequest(query="2019ApJ"),
    )
    assert options.total == 1
    assert options.items[0].value == bib_id


def test_patch_distance_method(manager: domain.ReferencesManager) -> None:
    manager.create_row(
        "distance",
        "methods",
        adminapi.CreateReferenceRowRequest(
            row={"id": "TRGB", "title": "Old title"},
        ),
    )
    manager.patch_row(
        "distance",
        "methods",
        adminapi.PatchReferenceRowRequest(
            key={"id": "TRGB"},
            changes={"title": "New title"},
        ),
    )

    rows = manager.list_rows(
        "distance",
        "methods",
        adminapi.ListReferenceRowsRequest(query="TRGB"),
    )
    assert rows.items[0].row["title"] == "New title"


def test_unknown_table_rejected(manager: domain.ReferencesManager) -> None:
    with pytest.raises(NotFoundError):
        manager.list_rows(
            "layer0",
            "tables",
            adminapi.ListReferenceRowsRequest(),
        )


def test_invalid_enum_rejected(manager: domain.ReferencesManager) -> None:
    with pytest.raises(RuleValidationError):
        manager.create_row(
            "distance",
            "methods",
            adminapi.CreateReferenceRowRequest(
                row={
                    "id": "BAD",
                    "indicator": "not-an-indicator",
                    "title": "Bad method",
                },
            ),
        )


def test_duplicate_primary_key_rejected(manager: domain.ReferencesManager) -> None:
    manager.create_row(
        "distance",
        "methods",
        adminapi.CreateReferenceRowRequest(
            row={"id": "TRGB", "title": "TRGB"},
        ),
    )
    with pytest.raises(ConflictError):
        manager.create_row(
            "distance",
            "methods",
            adminapi.CreateReferenceRowRequest(
                row={"id": "TRGB", "title": "Duplicate"},
            ),
        )


def test_missing_foreign_key_rejected(manager: domain.ReferencesManager) -> None:
    with pytest.raises(RuleValidationError):
        manager.create_row(
            "distance",
            "calibrations",
            adminapi.CreateReferenceRowRequest(
                row={
                    "id": "TRGB/F19",
                    "method_id": "missing-method",
                },
            ),
        )


def test_primary_key_update(manager: domain.ReferencesManager) -> None:
    manager.create_row(
        "distance",
        "methods",
        adminapi.CreateReferenceRowRequest(
            row={"id": "OLD", "title": "Method"},
        ),
    )
    manager.patch_row(
        "distance",
        "methods",
        adminapi.PatchReferenceRowRequest(
            key={"id": "OLD"},
            changes={"id": "NEW"},
        ),
    )

    rows = manager.list_rows(
        "distance",
        "methods",
        adminapi.ListReferenceRowsRequest(query="NEW"),
    )
    assert rows.total == 1
    assert rows.items[0].key == {"id": "NEW"}

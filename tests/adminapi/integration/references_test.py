import unittest

import structlog

from app.adminapi import domain, repository
from app.lib.storage import enums
from app.lib.web.errors import ConflictError, NotFoundError, RuleValidationError
from app.specs import adminapi
from tests import lib


class ReferencesManagerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = lib.TestPostgresStorage.get(enums.PG_ENUM_REGISTRY)
        cls.repo = repository.Repository(cls.pg_storage.get_storage(), structlog.get_logger())
        cls.manager = domain.ReferencesManager(cls.repo)

    def tearDown(self) -> None:
        self.pg_storage.clear()

    def test_create_and_list_distance_method(self) -> None:
        self.manager.create_row(
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

        rows = self.manager.list_rows(
            "distance",
            "methods",
            adminapi.ListReferenceRowsRequest(query="TRGB"),
        )
        self.assertEqual(rows.total, 1)
        self.assertEqual(rows.items[0].key, {"id": "TRGB"})
        self.assertEqual(rows.items[0].row["title"], "Tip of the red giant branch")

    def test_create_bib_and_calibration_with_reference_options(self) -> None:
        bib_id = self.repo.create_bibliography(
            "2019ApJ...887...80F",
            2019,
            ["Freedman W. L."],
            "The Carnegie-Chicago Hubble Program",
        )
        self.manager.create_row(
            "distance",
            "methods",
            adminapi.CreateReferenceRowRequest(
                row={
                    "id": "TRGB",
                    "title": "TRGB",
                },
            ),
        )
        self.manager.create_row(
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

        options = self.manager.list_field_options(
            "distance",
            "calibrations",
            "bib",
            adminapi.ListReferenceFieldOptionsRequest(query="2019ApJ"),
        )
        self.assertEqual(options.total, 1)
        self.assertEqual(options.items[0].value, bib_id)

    def test_patch_distance_method(self) -> None:
        self.manager.create_row(
            "distance",
            "methods",
            adminapi.CreateReferenceRowRequest(
                row={"id": "TRGB", "title": "Old title"},
            ),
        )
        self.manager.patch_row(
            "distance",
            "methods",
            adminapi.PatchReferenceRowRequest(
                key={"id": "TRGB"},
                changes={"title": "New title"},
            ),
        )

        rows = self.manager.list_rows(
            "distance",
            "methods",
            adminapi.ListReferenceRowsRequest(query="TRGB"),
        )
        self.assertEqual(rows.items[0].row["title"], "New title")

    def test_unknown_table_rejected(self) -> None:
        with self.assertRaises(NotFoundError):
            self.manager.list_rows(
                "layer0",
                "tables",
                adminapi.ListReferenceRowsRequest(),
            )

    def test_invalid_enum_rejected(self) -> None:
        with self.assertRaises(RuleValidationError):
            self.manager.create_row(
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

    def test_duplicate_primary_key_rejected(self) -> None:
        self.manager.create_row(
            "distance",
            "methods",
            adminapi.CreateReferenceRowRequest(
                row={"id": "TRGB", "title": "TRGB"},
            ),
        )
        with self.assertRaises(ConflictError):
            self.manager.create_row(
                "distance",
                "methods",
                adminapi.CreateReferenceRowRequest(
                    row={"id": "TRGB", "title": "Duplicate"},
                ),
            )

    def test_missing_foreign_key_rejected(self) -> None:
        with self.assertRaises(RuleValidationError):
            self.manager.create_row(
                "distance",
                "calibrations",
                adminapi.CreateReferenceRowRequest(
                    row={
                        "id": "TRGB/F19",
                        "method_id": "missing-method",
                    },
                ),
            )

    def test_primary_key_update(self) -> None:
        self.manager.create_row(
            "distance",
            "methods",
            adminapi.CreateReferenceRowRequest(
                row={"id": "OLD", "title": "Method"},
            ),
        )
        self.manager.patch_row(
            "distance",
            "methods",
            adminapi.PatchReferenceRowRequest(
                key={"id": "OLD"},
                changes={"id": "NEW"},
            ),
        )

        rows = self.manager.list_rows(
            "distance",
            "methods",
            adminapi.ListReferenceRowsRequest(query="NEW"),
        )
        self.assertEqual(rows.total, 1)
        self.assertEqual(rows.items[0].key, {"id": "NEW"})

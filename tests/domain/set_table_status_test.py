import unittest
import uuid
from unittest import mock

from astropy import units as u
from astropy.coordinates import ICRS

from app import commands, entities, schema
from app.domain.actions.set_table_status import assign_pgc, set_table_status
from app.lib import testing
from app.lib.storage import enums


class AssignPGCTest(unittest.TestCase):
    def setUp(self):
        self.depot = commands.get_mock_depot()

    def test_new_and_existing(self):
        testing.returns(self.depot.common_repo.generate_pgc, [1002, 1003, 1004, 123])
        testing.returns(self.depot.common_repo.upsert_pgc, None)

        original = [
            entities.ObjectProcessingInfo(
                str(uuid.uuid4()), enums.ObjectProcessingStatus.NEW, {}, entities.ObjectInfo()
            ),
            entities.ObjectProcessingInfo(
                str(uuid.uuid4()), enums.ObjectProcessingStatus.NEW, {}, entities.ObjectInfo()
            ),
            entities.ObjectProcessingInfo(
                str(uuid.uuid4()), enums.ObjectProcessingStatus.EXISTING, {}, entities.ObjectInfo(), 1001
            ),
            entities.ObjectProcessingInfo(
                str(uuid.uuid4()), enums.ObjectProcessingStatus.NEW, {}, entities.ObjectInfo()
            ),
            entities.ObjectProcessingInfo(
                str(uuid.uuid4()), enums.ObjectProcessingStatus.EXISTING, {}, entities.ObjectInfo(), 1005
            ),
            entities.ObjectProcessingInfo(
                str(uuid.uuid4()), enums.ObjectProcessingStatus.NEW, {}, entities.ObjectInfo()
            ),
            entities.ObjectProcessingInfo(
                str(uuid.uuid4()), enums.ObjectProcessingStatus.EXISTING, {}, entities.ObjectInfo(), 1010
            ),
        ]

        actual = assign_pgc(self.depot.common_repo, original)
        expected = [1002, 1003, 1001, 1004, 1005, 123, 1010]

        self.assertEqual([obj.pgc for obj in actual], expected)

    def test_only_new(self):
        testing.returns(self.depot.common_repo.generate_pgc, [1002, 1003, 1004])

        original = [
            entities.ObjectProcessingInfo(
                str(uuid.uuid4()), enums.ObjectProcessingStatus.NEW, {}, entities.ObjectInfo()
            ),
            entities.ObjectProcessingInfo(
                str(uuid.uuid4()), enums.ObjectProcessingStatus.NEW, {}, entities.ObjectInfo()
            ),
            entities.ObjectProcessingInfo(
                str(uuid.uuid4()), enums.ObjectProcessingStatus.NEW, {}, entities.ObjectInfo()
            ),
        ]

        actual = assign_pgc(self.depot.common_repo, original)
        expected = [1002, 1003, 1004]

        self.depot.common_repo.upsert_pgc.assert_not_called()
        self.assertEqual([obj.pgc for obj in actual], expected)

    def test_only_existing(self):
        testing.returns(self.depot.common_repo.upsert_pgc, None)

        original = [
            entities.ObjectProcessingInfo(
                str(uuid.uuid4()), enums.ObjectProcessingStatus.EXISTING, {}, entities.ObjectInfo(), 1001
            ),
            entities.ObjectProcessingInfo(
                str(uuid.uuid4()), enums.ObjectProcessingStatus.EXISTING, {}, entities.ObjectInfo(), 1005
            ),
            entities.ObjectProcessingInfo(
                str(uuid.uuid4()), enums.ObjectProcessingStatus.EXISTING, {}, entities.ObjectInfo(), 1010
            ),
        ]

        actual = assign_pgc(self.depot.common_repo, original)
        expected = [1001, 1005, 1010]

        self.depot.common_repo.generate_pgc.assert_not_called()
        self.assertEqual([obj.pgc for obj in actual], expected)

    def test_other_statuses(self):
        testing.returns(self.depot.common_repo.generate_pgc, [1002])
        testing.returns(self.depot.common_repo.upsert_pgc, None)

        original = [
            entities.ObjectProcessingInfo(
                str(uuid.uuid4()), enums.ObjectProcessingStatus.COLLIDED, {}, entities.ObjectInfo()
            ),
            entities.ObjectProcessingInfo(
                str(uuid.uuid4()), enums.ObjectProcessingStatus.EXISTING, {}, entities.ObjectInfo(), 12345
            ),
            entities.ObjectProcessingInfo(
                str(uuid.uuid4()), enums.ObjectProcessingStatus.NEW, {}, entities.ObjectInfo()
            ),
        ]

        actual = assign_pgc(self.depot.common_repo, original)
        expected = [12345, 1002]

        self.assertEqual([obj.pgc for obj in actual], expected)


class SetTableStatusTest(unittest.TestCase):
    def setUp(self):
        self.depot = commands.get_mock_depot()

    def test_one_batch_no_overrides(self):
        testing.returns(
            self.depot.layer0_repo.get_objects,
            [
                entities.ObjectProcessingInfo(
                    str(uuid.uuid4()),
                    enums.ObjectProcessingStatus.NEW,
                    {},
                    entities.ObjectInfo(coordinates=ICRS(ra=12.4 * u.deg, dec=11.4 * u.deg)),
                ),
                entities.ObjectProcessingInfo(
                    str(uuid.uuid4()),
                    enums.ObjectProcessingStatus.EXISTING,
                    {},
                    entities.ObjectInfo(coordinates=ICRS(ra=12.4 * u.deg, dec=11.4 * u.deg)),
                    123456,
                ),
                entities.ObjectProcessingInfo(
                    str(uuid.uuid4()),
                    enums.ObjectProcessingStatus.COLLIDED,
                    {"error": "collision"},
                    entities.ObjectInfo(coordinates=ICRS(ra=12.4 * u.deg, dec=11.4 * u.deg)),
                ),
            ],
        )

        testing.returns(self.depot.common_repo.upsert_pgc, None)
        testing.returns(self.depot.common_repo.generate_pgc, [1002])

        set_table_status(self.depot, schema.SetTableStatusRequest(table_id=1, batch_size=5, overrides=[]))

        self.depot.common_repo.upsert_pgc.assert_called_once_with([123456])
        self.depot.common_repo.generate_pgc.assert_called_once_with(1)

    def test_one_batch_with_overrides(self):
        obj2_id = str(uuid.uuid4())
        obj3_id = str(uuid.uuid4())
        testing.returns(
            self.depot.layer0_repo.get_objects,
            [
                entities.ObjectProcessingInfo(
                    str(uuid.uuid4()),
                    enums.ObjectProcessingStatus.NEW,
                    {},
                    entities.ObjectInfo(coordinates=ICRS(ra=12.4 * u.deg, dec=11.4 * u.deg)),
                ),
                entities.ObjectProcessingInfo(
                    obj2_id,
                    enums.ObjectProcessingStatus.EXISTING,
                    {},
                    entities.ObjectInfo(coordinates=ICRS(ra=12.4 * u.deg, dec=11.4 * u.deg)),
                    123456,
                ),
                entities.ObjectProcessingInfo(
                    obj3_id,
                    enums.ObjectProcessingStatus.COLLIDED,
                    {"error": "collision"},
                    entities.ObjectInfo(coordinates=ICRS(ra=12.4 * u.deg, dec=11.4 * u.deg)),
                ),
            ],
        )

        testing.returns(self.depot.common_repo.upsert_pgc, None)
        testing.returns(self.depot.common_repo.generate_pgc, [1234, 1235])

        set_table_status(
            self.depot,
            schema.SetTableStatusRequest(
                table_id=1,
                batch_size=5,
                overrides=[
                    schema.SetTableStatusOverrides(id=obj2_id),
                    schema.SetTableStatusOverrides(id=obj3_id, pgc=1234),
                ],
            ),
        )

        self.depot.common_repo.upsert_pgc.assert_called_once_with([1234])
        self.depot.common_repo.generate_pgc.assert_called_once_with(2)

    def test_multiple_batches(self):
        testing.returns(
            self.depot.layer0_repo.get_objects,
            [
                entities.ObjectProcessingInfo(
                    str(uuid.uuid4()),
                    enums.ObjectProcessingStatus.NEW,
                    {},
                    entities.ObjectInfo(coordinates=ICRS(ra=12.4 * u.deg, dec=11.4 * u.deg)),
                ),
                entities.ObjectProcessingInfo(
                    str(uuid.uuid4()),
                    enums.ObjectProcessingStatus.EXISTING,
                    {},
                    entities.ObjectInfo(coordinates=ICRS(ra=12.4 * u.deg, dec=11.4 * u.deg)),
                    123456,
                ),
                entities.ObjectProcessingInfo(
                    str(uuid.uuid4()),
                    enums.ObjectProcessingStatus.COLLIDED,
                    {"error": "collision"},
                    entities.ObjectInfo(coordinates=ICRS(ra=12.4 * u.deg, dec=11.4 * u.deg)),
                ),
            ],
        )
        testing.returns(
            self.depot.layer0_repo.get_objects,
            [
                entities.ObjectProcessingInfo(
                    str(uuid.uuid4()), enums.ObjectProcessingStatus.NEW, {}, entities.ObjectInfo(coordinates=ICRS(ra=12.4 * u.deg, dec=11.4 * u.deg))
                )
            ],
        )

        testing.returns(self.depot.common_repo.upsert_pgc, None)
        testing.returns(self.depot.common_repo.generate_pgc, [1234])
        testing.returns(self.depot.common_repo.generate_pgc, [1235])

        set_table_status(self.depot, schema.SetTableStatusRequest(table_id=1, batch_size=3, overrides=[]))

        self.depot.common_repo.upsert_pgc.assert_called_once_with([123456])
        self.depot.common_repo.generate_pgc.assert_has_calls([mock.call(1), mock.call(1)])

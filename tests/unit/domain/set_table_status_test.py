import unittest
import uuid
from unittest import mock

from astropy import units as u
from astropy.coordinates import ICRS

from app import entities
from app.domain import adminapi as domain
from app.domain.adminapi.table_transfer import assign_pgc
from app.lib.storage import enums
from app.presentation import adminapi as presentation
from tests import lib


class AssignPGCTest(unittest.TestCase):
    def setUp(self):
        self.manager = domain.TableTransferManager(
            common_repo=mock.MagicMock(),
            layer0_repo=mock.MagicMock(),
            layer1_repo=mock.MagicMock(),
            layer2_repo=mock.MagicMock(),
        )

    def test_new_and_existing(self):
        lib.returns(self.manager.common_repo.generate_pgc, [1002, 1003, 1004, 123])
        lib.returns(self.manager.common_repo.upsert_pgc, None)

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

        actual = assign_pgc(self.manager.common_repo, original)
        expected = [1002, 1003, 1001, 1004, 1005, 123, 1010]

        self.assertEqual([obj.pgc for obj in actual], expected)

    def test_only_new(self):
        lib.returns(self.manager.common_repo.generate_pgc, [1002, 1003, 1004])

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

        actual = assign_pgc(self.manager.common_repo, original)
        expected = [1002, 1003, 1004]

        self.manager.common_repo.upsert_pgc.assert_not_called()
        self.assertEqual([obj.pgc for obj in actual], expected)

    def test_only_existing(self):
        lib.returns(self.manager.common_repo.upsert_pgc, None)

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

        actual = assign_pgc(self.manager.common_repo, original)
        expected = [1001, 1005, 1010]

        self.manager.common_repo.generate_pgc.assert_not_called()
        self.assertEqual([obj.pgc for obj in actual], expected)

    def test_other_statuses(self):
        lib.returns(self.manager.common_repo.generate_pgc, [1002])
        lib.returns(self.manager.common_repo.upsert_pgc, None)

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

        actual = assign_pgc(self.manager.common_repo, original)
        expected = [12345, 1002]

        self.assertEqual([obj.pgc for obj in actual], expected)


class SetTableStatusTest(unittest.TestCase):
    def setUp(self):
        self.manager = domain.TableTransferManager(
            common_repo=mock.MagicMock(),
            layer0_repo=mock.MagicMock(),
            layer1_repo=mock.MagicMock(),
            layer2_repo=mock.MagicMock(),
        )

    def test_one_batch_no_overrides(self):
        lib.returns(
            self.manager.layer0_repo.get_objects,
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

        lib.returns(self.manager.common_repo.upsert_pgc, None)
        lib.returns(self.manager.common_repo.generate_pgc, [1002])

        self.manager.set_table_status(presentation.SetTableStatusRequest(table_id=1, batch_size=5, overrides=[]))

        self.manager.common_repo.upsert_pgc.assert_called_once_with([123456])
        self.manager.common_repo.generate_pgc.assert_called_once_with(1)

    def test_one_batch_with_overrides(self):
        obj2_id = str(uuid.uuid4())
        obj3_id = str(uuid.uuid4())
        lib.returns(
            self.manager.layer0_repo.get_objects,
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

        lib.returns(self.manager.common_repo.upsert_pgc, None)
        lib.returns(self.manager.common_repo.generate_pgc, [1234, 1235])

        self.manager.set_table_status(
            presentation.SetTableStatusRequest(
                table_id=1,
                batch_size=5,
                overrides=[
                    presentation.SetTableStatusOverrides(id=obj2_id),
                    presentation.SetTableStatusOverrides(id=obj3_id, pgc=1234),
                ],
            ),
        )

        self.manager.common_repo.upsert_pgc.assert_called_once_with([1234])
        self.manager.common_repo.generate_pgc.assert_called_once_with(2)

    def test_multiple_batches(self):
        lib.returns(
            self.manager.layer0_repo.get_objects,
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
        lib.returns(
            self.manager.layer0_repo.get_objects,
            [
                entities.ObjectProcessingInfo(
                    str(uuid.uuid4()),
                    enums.ObjectProcessingStatus.NEW,
                    {},
                    entities.ObjectInfo(coordinates=ICRS(ra=12.4 * u.deg, dec=11.4 * u.deg)),
                )
            ],
        )

        lib.returns(self.manager.common_repo.upsert_pgc, None)
        lib.returns(self.manager.common_repo.generate_pgc, [1234])
        lib.returns(self.manager.common_repo.generate_pgc, [1235])

        self.manager.set_table_status(presentation.SetTableStatusRequest(table_id=1, batch_size=3, overrides=[]))

        self.manager.common_repo.upsert_pgc.assert_called_once_with([123456])
        self.manager.common_repo.generate_pgc.assert_has_calls([mock.call(1), mock.call(1)])

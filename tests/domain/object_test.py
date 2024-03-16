import unittest

from app.data import repository
from app.domain import model, usecases
from app.lib import testing


class ObjectTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = testing.TestPostgresStorage("postgres/migrations")
        cls.storage.start()

        cls.repo = repository.DataRespository(cls.storage.get_storage())
        cls.actions = usecases.Actions(cls.repo)

    @classmethod
    def tearDownClass(cls):
        cls.storage.stop()

    def tearDown(self):
        self.storage.clear()

    def test_create_object_success(self):
        source_response = self.actions.create_source(
            model.CreateSourceRequest(
                "publication",
                dict(bibcode="1992ApJ…400L…1W", author="Test author et al.", year=2000, title="Test research"),
            )
        )
        object_response = self.actions.create_object(
            model.CreateObjectRequest(
                source_id=source_response.id,
                object=model.ObjectInfo(
                    name="M33",
                    type="galaxy",
                    position=model.PositionInfo(
                        coordinate_system="equatorial",
                        epoch="J2000",
                        coords=model.CoordsInfo(ra=200.5, dec=-52.5),
                    ),
                ),
            )
        )
        names = self.actions.get_object_names(model.GetObjectNamesRequest(object_response.id, 20, 0))

        self.assertEqual(len(names.names), 1)
        self.assertEqual(names.names[0].name, "M33")
        self.assertEqual(names.names[0].source_id, source_response.id)

    def test_create_object_without_source(self):
        with self.assertRaises(Exception):
            _ = self.actions.create_object(
                model.CreateObjectRequest(
                    source_id=123,
                    object=model.ObjectInfo(
                        name="M33",
                        type="galaxy",
                        position=model.PositionInfo(
                            coordinate_system="equatorial",
                            epoch="J2000",
                            coords=model.CoordsInfo(ra=200.5, dec=-52.5),
                        ),
                    ),
                )
            )

import unittest

from astropy import units as u

from app.data import model
from app.domain import converters
from app.domain.processing.mark_objects import get_converters


class TestGetConverters(unittest.TestCase):
    def test_valid_columns(self):
        columns = [
            model.ColumnDescription("name", "text", ucd="meta.id"),
            model.ColumnDescription("ra", "float", ucd="pos.eq.ra", unit=u.rad),
            model.ColumnDescription("dec", "float", ucd="pos.eq.dec", unit=u.rad),
        ]

        expected = {
            converters.ICRSConverter.name(),
            converters.NameConverter.name(),
        }

        actual = get_converters(columns)

        self.assertEqual(expected, {a.name() for a in actual})

    def test_unparsable_columns(self):
        columns = [
            model.ColumnDescription("name", "text"),
            model.ColumnDescription("ra", "float", unit=u.rad),
            model.ColumnDescription("dec", "float", unit=u.rad),
        ]

        with self.assertRaises(RuntimeError):
            get_converters(columns)

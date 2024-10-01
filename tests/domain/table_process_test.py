import datetime
import unittest
import uuid
from unittest import mock

import astropy.units as u
import pandas
from astropy.coordinates import ICRS

from app import entities, schema
from app.commands.depot import Depot
from app.domain import converters
from app.domain.actions.create_table import INTERNAL_ID_COLUMN_NAME
from app.domain.actions.table_process import cross_identification_func_type, table_process_with_cross_identification
from app.domain.model.layer2.layer_2_model import Layer2Model
from app.domain.model.params import cross_identification_result as result
from app.lib.storage import enums
from app.lib.web import errors


def get_noop_cross_identification(
    results: list[result.CrossIdentifyResult],
) -> cross_identification_func_type:
    return lambda layer2_repo, obj, provider, user_param: results.pop(0)


class TableProcessTest(unittest.TestCase):
    def setUp(self):
        self.layer0_repo = mock.MagicMock()
        self.layer2_repo = mock.MagicMock()
        self.depot = Depot(
            mock.MagicMock(),
            self.layer0_repo,
            self.layer2_repo,
            mock.MagicMock(),
            mock.MagicMock(),
            mock.MagicMock(),
            mock.MagicMock(),
        )

    def test_invalid_table(self):
        self.layer0_repo.fetch_metadata.side_effect = [
            entities.Layer0Creation(
                table_name="table_name",
                column_descriptions=[
                    entities.ColumnDescription("ra", "float", ucd="pos.eq.ra", unit="h"),
                ],
                bibliography_id=1234,
                datatype=enums.DataType.REGULAR,
            )
        ]

        ci_func = get_noop_cross_identification([])

        with self.assertRaises(errors.LogicalError):
            table_process_with_cross_identification(
                self.depot,
                ci_func,
                schema.TableProcessRequest(
                    table_id=1234,
                    cross_identification=schema.CrossIdentification(1.5, 4.5),
                ),
            )

    def test_objects(self):
        objects = [
            ("obj1", 10.0, 10.0, result.CrossIdentifyResult(None, None), enums.ObjectProcessingStatus.NEW, {}),
            (
                "obj2",
                20.0,
                20.0,
                result.CrossIdentifyResult(
                    Layer2Model(1234, ICRS(), [], "obj1", 1, 2, datetime.datetime.now(tz=datetime.timezone.utc)), None
                ),
                enums.ObjectProcessingStatus.EXISTING,
                {"pgc": 1234},
            ),
            (
                "obj3",
                30.0,
                30.0,
                result.CrossIdentifyResult(None, result.CrossIdentificationNamesNotFoundException(["obj2"])),
                enums.ObjectProcessingStatus.COLLIDED,
                {"error": result.CrossIdentificationNamesNotFoundException(["obj2"])},  # TODO: convert to dataclasses?
            ),
        ]

        self.layer0_repo.fetch_metadata.side_effect = [
            entities.Layer0Creation(
                table_name="table_name",
                column_descriptions=[
                    entities.ColumnDescription("objname", "str", ucd="meta.id"),
                    entities.ColumnDescription("ra", "float", ucd="pos.eq.ra", unit=u.hourangle),
                    entities.ColumnDescription("dec", "float", ucd="pos.eq.dec", unit=u.deg),
                ],
                bibliography_id=1234,
                datatype=enums.DataType.REGULAR,
            )
        ]

        data = pandas.DataFrame()
        ci_results = []
        expected = []

        for name, ra, dec, res, status, metadata in objects:
            curr_obj = pandas.DataFrame(
                {INTERNAL_ID_COLUMN_NAME: [str(uuid.uuid4())], "objname": [name], "ra": [ra], "dec": [dec]}
            )
            data = pandas.concat([data, curr_obj])

            ci_results.append(res)
            expected.append((status, metadata))

        self.layer0_repo.fetch_raw_data.side_effect = [
            entities.Layer0RawData(table_id=1234, data=data),
            entities.Layer0RawData(table_id=1234, data=pandas.DataFrame()),
        ]

        ci_func = get_noop_cross_identification(ci_results)

        table_process_with_cross_identification(
            self.depot,
            ci_func,
            schema.TableProcessRequest(
                table_id=1234,
                cross_identification=schema.CrossIdentification(1.5, 4.5),
            ),
        )

        calls = self.layer0_repo.upsert_object.call_args_list
        self.assertEqual(len(calls), len(expected))

        for call, (status, metadata) in zip(calls, expected):
            self.assertEqual(call.args[2], status)
            self.assertEqual(call.args[3], metadata)

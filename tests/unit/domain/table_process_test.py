import unittest
import uuid
from unittest import mock

import astropy.units as u
import pandas

from app.data import model, repositories
from app.domain import adminapi as domain
from app.domain.model.params import cross_identification_result as result
from app.domain.usecases.cross_identification import (
    cross_identification_func_type,
)
from app.lib.storage import enums
from app.presentation import adminapi as presentation
from tests import lib


def get_noop_cross_identification(
    results: list[result.CrossIdentifyResult],
) -> cross_identification_func_type:
    return lambda layer2_repo, obj, provider, user_param: results.pop(0)


class TableProcessTest(unittest.TestCase):
    def setUp(self):
        self.manager = domain.TableTransferManager(
            common_repo=mock.MagicMock(),
            layer0_repo=mock.MagicMock(),
            layer1_repo=mock.MagicMock(),
            layer2_repo=mock.MagicMock(),
        )

    def test_objects(self):
        objects = [
            ("obj1", 10.0, 10.0, result.CrossIdentifyResult(None, None), enums.ObjectProcessingStatus.NEW, {}, None),
        ]

        lib.returns(
            self.manager.layer0_repo.fetch_metadata,
            model.Layer0Creation(
                table_name="table_name",
                column_descriptions=[
                    model.ColumnDescription("objname", "str", ucd="meta.id"),
                    model.ColumnDescription("ra", "float", ucd="pos.eq.ra", unit=u.hourangle),
                    model.ColumnDescription("dec", "float", ucd="pos.eq.dec", unit=u.deg),
                ],
                bibliography_id=1234,
                datatype=enums.DataType.REGULAR,
            ),
        )

        data = pandas.DataFrame()
        ci_results = []
        expected = []

        for name, ra, dec, res, status, metadata, pgc in objects:
            curr_obj = pandas.DataFrame(
                {repositories.INTERNAL_ID_COLUMN_NAME: [str(uuid.uuid4())], "objname": [name], "ra": [ra], "dec": [dec]}
            )
            data = pandas.concat([data, curr_obj])

            ci_results.append(res)
            expected.append((status, metadata, pgc))

        lib.returns(self.manager.layer0_repo.fetch_raw_data, model.Layer0RawData(table_id=1234, data=data))
        lib.returns(
            self.manager.layer0_repo.fetch_raw_data, model.Layer0RawData(table_id=1234, data=pandas.DataFrame())
        )

        self.manager.table_process(
            presentation.TableProcessRequest(
                table_id=1234,
                cross_identification=presentation.CrossIdentification(1.5, 4.5),
            ),
        )

        calls = self.manager.layer0_repo.upsert_old_object.call_args_list
        self.assertEqual(len(calls), len(expected))

        for call, (status, metadata, pgc) in zip(calls, expected, strict=False):
            self.assertEqual(call.args[1].status, status)
            self.assertEqual(call.args[1].metadata, metadata)
            if pgc is not None:
                self.assertEqual(call.args[1].pgc, pgc)

import hashlib
import json
import uuid

import pandas

import app.domain.actions.create_table as create_table
from app import commands, schema
from app.data import model as data_model


def add_data(depot: commands.Depot, r: schema.AddDataRequest) -> schema.AddDataResponse:
    data_df = pandas.DataFrame.from_records(r.data)
    data_df[create_table.INTERNAL_ID_COLUMN_NAME] = data_df.apply(_compute_hash, axis=1)
    data_df = data_df.drop_duplicates(subset=create_table.INTERNAL_ID_COLUMN_NAME, keep="last")

    with depot.layer0_repo.with_tx() as tx:
        depot.layer0_repo.insert_raw_data(
            data_model.Layer0RawData(
                table_id=r.table_id,
                data=data_df,
            ),
            tx=tx,
        )

    return schema.AddDataResponse()


def _compute_hash(row: pandas.Series) -> str:
    """
    This function applies special algorithm to an iterable to compute stable hash.
    It ensures that values are sorted and that spacing is not an issue.
    """
    data = []

    for key, val in dict(row).items():
        data.append([key, val])

    data = sorted(data, key=lambda t: t[0])
    data_string = json.dumps(data, separators=(",", ":"))

    return _hashfunc(data_string)


def _hashfunc(string: str) -> str:
    return str(uuid.UUID(hashlib.md5(string.encode("utf-8"), usedforsecurity=False).hexdigest()))

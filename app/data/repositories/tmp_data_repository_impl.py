import random
import string
from typing import Any, Sequence

import astropy.units as u
import numpy as np
from pandas import DataFrame, Series

from app.data import template
from app.domain.model.params import TmpCoordinateTableQueryParam, TmpDataRepositoryQueryParam, TmpNameTableQueryParam
from app.domain.repositories.tmp_data_repository import TmpDataRepository
from app.lib.storage import mapping, postgres


def _extended_type_map(series: Series):
    if series.size > 0 and isinstance(series[0], Sequence):
        internal_tp = mapping.get_type_from_dtype(np.array(series[0]).dtype)
        return f"{internal_tp}[]"

    return mapping.get_type_from_dtype(series.dtype)


class TmpDataRepositoryImpl(TmpDataRepository, postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage):
        self._storage = storage

    def make_table(self, data: DataFrame, index_on: list[str] | None) -> str:
        name = "".join(random.choices(string.ascii_lowercase, k=32))

        isinstance(data["name"][0], Sequence)
        fields = [(col_name, _extended_type_map(data[col_name])) for col_name in data.columns.values]

        with self.with_tx():
            self._storage.exec(
                template.render_query(
                    template.CREATE_TMP_TABLE,
                    name=name,
                    fields=fields,
                )
            )

            fields = data.columns

            self._storage.execute_many(
                template.render_query(
                    template.INSERT_TMP_RAW_DATA,
                    table=name,
                    fields=fields,
                ),
                params=data.to_numpy().tolist(),
            )
            if index_on is not None:
                self._storage.exec(
                    template.render_query(
                        template.BUILD_INDEX, index_name=f"index_{name}", table_name=name, columns=index_on
                    ),
                )

        return name

    def query_table(self, param: TmpDataRepositoryQueryParam) -> list[dict[str, Any]]:
        if isinstance(param, TmpCoordinateTableQueryParam):
            delta = param.r.to(u.deg).value
            ra0 = param.center.ra.to(u.deg).value
            dec0 = param.center.dec.to(u.deg).value
            return self._storage.query(
                template.render_query(
                    template.GET_TMP_DATA_INSIDE, table_name=param.table_name(), delta=delta, ra0=ra0, dec0=dec0
                )
            )

        if isinstance(param, TmpNameTableQueryParam):
            return self._storage.query(
                template.render_query(
                    template.GET_TMP_DATA_BY_NAME, table_name=param.table_name(), all_names=param.names
                ),
                params=[],
            )

        raise ValueError(f"Unexpected query param: {param}")

    def drop_table(self, name: str):
        self._storage.exec(template.render_query(template.DROP_TABLE, table_name=name))

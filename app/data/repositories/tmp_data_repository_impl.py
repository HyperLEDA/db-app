import string
import random
from typing import Any

import astropy.units as u

from pandas import DataFrame

from app.data import template
from app.domain.model.params import TmpDataRepositoryQueryParam, TmpCoordinateTableQueryParam
from app.domain.repositories.tmp_data_repository import TmpDataRepository
from app.lib.storage import postgres
from app.lib.storage import mapping


class TmpDataRepositoryImpl(TmpDataRepository):
    def __init__(self, storage: postgres.PgStorage):
        self._storage = storage

    async def make_table(self, data: DataFrame, index_on: list[str] | None) -> str:
        name = ''.join(random.choices(string.ascii_lowercase, k=32))

        fields = [
            (col_name, mapping.get_type_from_dtype(data[col_name].dtype))
            for col_name in data.columns.values
        ]

        with self._storage.with_tx() as tx:
            self._storage.exec(
                template.render_query(
                    template.CREATE_TMP_TABLE,
                    name=name,
                    fields=fields,
                )
            )

            fields = data.columns

            for row in data.to_dict(orient="records"):
                obj = {}
                params = []
                for field in fields:
                    value = row[field]
                    params.append(value)
                    obj[field] = "%s"

                self._storage.exec(
                    template.render_query(
                        template.INSERT_TMP_RAW_DATA,
                        table=name,
                        fields=fields,
                        objects=[obj],
                    ),
                    params=params,
                    tx=tx,
                )
            if index_on is not None:
                self._storage.exec(
                    template.render_query(
                        template.BUILD_INDEX,
                        index_name=f"index_{name}",
                        table_name=name,
                        columns=index_on
                    ),
                    tx=tx
                )

        return name

    async def query_table(self, param: TmpDataRepositoryQueryParam) -> list[dict[str, Any]]:
        if isinstance(param, TmpCoordinateTableQueryParam):
            delta = param.r.to(u.deg).value
            ra0 = param.center.ra.to(u.deg).value
            dec0 = param.center.dec.to(u.deg).value
            return self._storage.query(template.render_query(
                template.GET_TMP_DATA_INSIDE,
                table_name=param.table_name(),
                delta=delta,
                ra0=ra0,
                dec0=dec0
            ))

        raise ValueError(f"Unexpected query param: {param}")

    async def drop_table(self, name: str):
        self._storage.exec(template.render_query(template.DROP_TABLE, table_name=name))

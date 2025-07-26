import datetime
import json

import numpy as np
import pandas
import structlog
from astropy import table
from astropy import units as u

from app.data import model, repositories, template
from app.data.repositories.layer0.common import RAWDATA_SCHEMA
from app.lib.storage import postgres
from app.lib.web.errors import DatabaseError

log: structlog.stdlib.BoundLogger = structlog.get_logger()


class Layer0TableRepository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage) -> None:
        super().__init__(storage)

    def create_table(self, data: model.Layer0TableMeta) -> model.Layer0CreationResponse:
        """
        Creates table, writes metadata and returns integer that identifies the table for
        further requests. If table already exists, returns its ID instead of creating a new one.
        """
        table_id, ok = self._get_table_id(data.table_name)
        if ok:
            return model.Layer0CreationResponse(table_id, False)

        fields = []

        for column_descr in data.column_descriptions:
            constraint = ""
            if column_descr.is_primary_key:
                constraint = "PRIMARY KEY"

            fields.append((column_descr.name, column_descr.data_type, constraint))

        with self.with_tx():
            row = self._storage.query_one(
                template.INSERT_TABLE_REGISTRY_ITEM,
                params=[data.bibliography_id, data.table_name, data.datatype],
            )
            table_id = int(row.get("id"))

            self._storage.exec(
                template.render_query(
                    template.CREATE_TABLE,
                    schema=RAWDATA_SCHEMA,
                    name=data.table_name,
                    fields=fields,
                )
            )

            if data.description is not None:
                self._storage.exec(
                    "SELECT meta.setparams(%s, %s, %s::json)",
                    params=[RAWDATA_SCHEMA, data.table_name, json.dumps({"description": data.description})],
                )

            for column_descr in data.column_descriptions:
                self.update_column_metadata(data.table_name, column_descr)

        return model.Layer0CreationResponse(table_id, True)

    def insert_raw_data(self, data: model.Layer0RawData) -> None:
        """
        This method puts everything in parameters for prepared statement. This should not be a big
        issue but one would be better off using this function in batches since prepared statements make
        this quite cheap (excluding network slow down, though).
        """

        if len(data.data) == 0:
            log.warn("trying to insert 0 rows into the table", table_id=data.table_id)
            return

        row = self._storage.query_one(template.GET_RAWDATA_TABLE, params=[data.table_id])
        table_name = row.get("table_name")

        if table_name is None:
            raise DatabaseError(f"unable to fetch table with id {data.table_id}")

        fields = data.data.columns

        values = []
        params = []

        for row in data.data.to_dict(orient="records"):
            for field in fields:
                value = row[field]
                if type(value) in (int, float) and np.isnan(value):
                    value = None

                params.append(value)

            values.append(f"({','.join(['%s'] * len(fields))})")

        fields = [f'"{field}"' for field in fields]

        query = f"""
        INSERT INTO rawdata."{table_name}" ({",".join(fields)})
        VALUES {",".join(values)}
        ON CONFLICT DO NOTHING
        """

        self._storage.exec(query, params=params)

    def fetch_table(
        self,
        table_name: str,
        offset: str | None = None,
        columns: list[str] | None = None,
        order_column: str | None = None,
        order_direction: str = "asc",
        limit: int | None = None,
    ) -> table.Table:
        """
        :param table_id: ID of the raw table
        :param columns: select only given columns
        :param order_column: orders result by a provided column
        :param order_direction: if `order_column` is specified, sets order direction. Either `asc` or `desc`.
        :param offset: allows to retrieve rows starting from the `offset` object_id
        :param limit: allows to retrieve no more than `limit` rows
        """

        meta = self.fetch_metadata_by_name(table_name)

        columns_str = ",".join(columns or ["*"])

        params = []
        query = f"""
        SELECT {columns_str} FROM {RAWDATA_SCHEMA}."{table_name}"\n
        """

        if offset is not None:
            query += f"WHERE {repositories.INTERNAL_ID_COLUMN_NAME} > %s\n"
            params.append(offset)

        if order_column is not None:
            query += f"ORDER BY {order_column} {order_direction}\n"

        if limit is not None:
            query += "LIMIT %s\n"
            params.append(limit)

        rows = self._storage.query(query, params=params)
        df = pandas.DataFrame(rows)
        tbl = table.Table()
        if len(df) == 0:
            return tbl

        for col in meta.column_descriptions:
            values = df[col.name]

            if col.unit is not None:
                try:
                    if isinstance(col.unit, u.LogUnit):
                        values = u.Quantity(col.unit.to_physical(values), col.unit.physical_unit)
                    else:
                        values = u.Quantity(values, col.unit)
                except Exception:
                    pass

            tbl[col.name] = values

        return tbl

    def fetch_raw_data(
        self,
        table_id: int,
        offset: str | None = None,
        columns: list[str] | None = None,
        order_column: str | None = None,
        order_direction: str = "asc",
        limit: int | None = None,
    ) -> model.Layer0RawData:
        """
        :param table_id: ID of the raw table
        :param columns: select only given columns
        :param order_column: orders result by a provided column
        :param order_direction: if `order_column` is specified, sets order direction. Either `asc` or `desc`.
        :param offset: allows to retrieve rows starting from the `offset` object_id
        :param limit: allows to retrieve no more than `limit` rows
        :return: Layer0RawData
        """
        row = self._storage.query_one(template.GET_RAWDATA_TABLE, params=[table_id])
        table_name = row.get("table_name")

        if table_name is None:
            raise DatabaseError(f"unable to fetch table with id {table_id}")

        columns_str = ",".join(columns or ["*"])

        params = []
        query = f"""
        SELECT {columns_str} FROM {RAWDATA_SCHEMA}."{table_name}"\n
        """

        if offset is not None:
            query += f"WHERE {repositories.INTERNAL_ID_COLUMN_NAME} > %s\n"
            params.append(offset)

        if order_column is not None:
            query += f"ORDER BY {order_column} {order_direction}\n"

        if limit is not None:
            query += "LIMIT %s\n"
            params.append(limit)

        rows = self._storage.query(query, params=params)
        return model.Layer0RawData(table_id, pandas.DataFrame(rows))

    def fetch_metadata(self, table_id: int) -> model.Layer0TableMeta:
        row = self._storage.query_one(template.GET_RAWDATA_TABLE, params=[table_id])
        table_name = row.get("table_name")
        modification_dt: datetime.datetime | None = row.get("modification_dt")

        if table_name is None:
            raise DatabaseError(f"unable to fetch table with id {table_id}")

        return self._fetch_metadata_by_name(table_name, modification_dt)

    def fetch_metadata_by_name(self, table_name: str) -> model.Layer0TableMeta:
        row = self._storage.query_one(template.FETCH_RAWDATA_REGISTRY, params=[table_name])
        if row is None:
            raise DatabaseError(f"unable to fetch table with name {table_name}")

        modification_dt: datetime.datetime | None = row.get("modification_dt")
        return self._fetch_metadata_by_name(table_name, modification_dt)

    def _fetch_metadata_by_name(
        self, table_name: str, modification_dt: datetime.datetime | None
    ) -> model.Layer0TableMeta:
        column_descriptions = self._storage.query(
            "SELECT column_name, param FROM meta.column_info WHERE schema_name=%s AND table_name=%s",
            params=[RAWDATA_SCHEMA, table_name],
        )

        descriptions = []
        for description in column_descriptions:
            column_name = description["column_name"]
            metadata = description["param"]

            unit = None
            if metadata.get("unit") is not None:
                unit = u.Unit(metadata["unit"])

            descriptions.append(
                model.ColumnDescription(
                    column_name,
                    metadata["data_type"],
                    unit=unit,
                    description=metadata["description"],
                    ucd=metadata.get("ucd"),
                )
            )

        table_metadata = self._storage.query_one(template.FETCH_TABLE_METADATA, params=[RAWDATA_SCHEMA, table_name])
        registry_item = self._storage.query_one(template.FETCH_RAWDATA_REGISTRY, params=[table_name])

        if table_metadata is None:
            raise DatabaseError(f"unable to metadata for table {table_name}")

        return model.Layer0TableMeta(
            table_name,
            descriptions,
            registry_item["bib"],
            registry_item["datatype"],
            modification_dt,
            table_metadata["param"].get("description"),
            table_id=registry_item["id"],
        )

    def update_column_metadata(self, table_name: str, column_description: model.ColumnDescription) -> None:
        table_id, _ = self._get_table_id(table_name)

        column_params = {
            "description": column_description.description,
            "data_type": column_description.data_type,
        }

        if column_description.unit is not None:
            column_params["unit"] = column_description.unit.to_string()

        if column_description.ucd is not None:
            column_params["ucd"] = column_description.ucd

        modification_query = "UPDATE rawdata.tables SET modification_dt = now() WHERE id = %s"

        with self.with_tx():
            self._storage.exec(
                "SELECT meta.setparams(%s, %s, %s, %s::json)",
                params=[RAWDATA_SCHEMA, table_name, column_description.name, json.dumps(column_params)],
            )
            self._storage.exec(modification_query, params=[table_id])

    def _get_table_id(self, table_name: str) -> tuple[int, bool]:
        try:
            row = self._storage.query_one(
                "SELECT id FROM rawdata.tables WHERE table_name = %s",
                params=[table_name],
            )
        except RuntimeError:
            return 0, False

        return row["id"], True

    def _get_table_name(self, table_id: int) -> str:
        row = self._storage.query_one(
            "SELECT table_name FROM rawdata.tables WHERE id = %s",
            params=[table_id],
        )
        return row["table_name"]

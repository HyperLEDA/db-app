import json

from app.data import model, template
from app.lib.storage import postgres
from app.lib.web.errors import DatabaseError


class Layer0ModifiersRepository(postgres.TransactionalPGRepository):
    def get_modifiers(self, table_name: str) -> list[model.Modifier]:
        table_id_row = self._storage.query_one(template.FETCH_RAWDATA_REGISTRY, params=[table_name])
        if table_id_row is None:
            raise DatabaseError(f"unable to fetch table with name {table_name}")

        table_id = table_id_row["id"]

        rows = self._storage.query(
            """
            SELECT column_name, modifier_name, params
            FROM layer0.column_modifiers
            WHERE table_id = %s
            ORDER BY sequence
            """,
            params=[table_id],
        )

        return [
            model.Modifier(row["column_name"], row["modifier_name"], row["params"] if row["params"] else {})
            for row in rows
        ]

    def add_modifiers(self, table_name: str, modifiers: list[model.Modifier]) -> None:
        table_id_row = self._storage.query_one(template.FETCH_RAWDATA_REGISTRY, params=[table_name])
        if table_id_row is None:
            raise DatabaseError(f"unable to fetch table with name {table_name}")

        table_id = table_id_row["id"]

        query = """
        INSERT INTO layer0.column_modifiers (table_id, column_name, modifier_name, params, sequence) VALUES"""

        params = []
        values = []
        for sequence, modifier in enumerate(modifiers):
            params.extend(
                [
                    table_id,
                    modifier.column_name,
                    modifier.modifier_name,
                    json.dumps(modifier.params),
                    sequence,
                ]
            )
            values.append("(%s, %s, %s, %s, %s)")

        query = (
            query + ", ".join(values) + " ON CONFLICT (table_id, column_name, sequence) DO UPDATE SET "
            "modifier_name = EXCLUDED.modifier_name, params = EXCLUDED.params"
        )

        self._storage.exec(query, params=params)

import json

from app.data import model
from app.lib.storage import postgres


class Layer0ModifiersRepository(postgres.TransactionalPGRepository):
    def get_modifiers(self, table_id: int) -> list[model.Modifier]:
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

    def add_modifiers(self, table_id: int, modifiers: list[model.Modifier]) -> None:
        query = """
        INSERT INTO layer0.column_modifiers (table_id, column_name, modifier_name, params, sequence) VALUES"""

        params = []
        values = []
        for sequence, modifier in enumerate(modifiers):
            params.extend(
                [table_id, modifier.column_name, modifier.modifier_name, json.dumps(modifier.params), sequence]
            )
            values.append("(%s, %s, %s, %s, %s)")

        query = (
            query + ", ".join(values) + " ON CONFLICT (table_id, column_name, sequence) DO UPDATE SET "
            "modifier_name = EXCLUDED.modifier_name, params = EXCLUDED.params"
        )

        self._storage.exec(query, params=params)

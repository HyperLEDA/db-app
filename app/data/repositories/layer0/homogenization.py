import json

from app.data import model
from app.lib.storage import postgres


class Layer0HomogenizationRepository(postgres.TransactionalPGRepository):
    def get_homogenization_rules(self) -> list[model.HomogenizationRule]:
        rows = self._storage.query(
            """
            SELECT catalog, parameter, key, filters, priority, enrichment
            FROM layer0.homogenization_rules
            """
        )

        return [
            model.HomogenizationRule(
                row["catalog"],
                row["parameter"],
                row["filters"] if row["filters"] else {},
                row["key"],
                row["priority"],
                row["enrichment"] if row["enrichment"] else {},
            )
            for row in rows
        ]

    def get_homogenization_params(self) -> list[model.HomogenizationParams]:
        rows = self._storage.query(
            """
            SELECT catalog, key, params
            FROM layer0.homogenization_params
            """
        )

        return [
            model.HomogenizationParams(
                row["catalog"],
                row["params"],
                row["key"],
            )
            for row in rows
        ]

    def add_homogenization_rules(self, rules: list[model.HomogenizationRule]) -> None:
        query = """
        INSERT INTO layer0.homogenization_rules (catalog, parameter, key, filters, priority, enrichment) VALUES"""

        params = []
        values = []
        for rule in rules:
            params.extend(
                [
                    rule.catalog,
                    rule.parameter,
                    rule.key,
                    json.dumps(rule.filters),
                    rule.priority,
                    json.dumps(rule.enrichment) if rule.enrichment else None,
                ]
            )
            values.append("(%s, %s, %s, %s, %s, %s)")

        self._storage.exec(query + ", ".join(values), params=params)

    def add_homogenization_params(self, params: list[model.HomogenizationParams]) -> None:
        query = """
        INSERT INTO layer0.homogenization_params (catalog, key, params) VALUES"""

        query_params = []
        values = []

        for param in params:
            query_params.extend([param.catalog, param.key, json.dumps(param.params)])
            values.append("(%s, %s, %s)")

        query = query + ", ".join(values) + " ON CONFLICT (catalog, key) DO UPDATE SET params = EXCLUDED.params"

        self._storage.exec(query, params=query_params)

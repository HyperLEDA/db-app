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
                row["key"],
                row["filters"],
                row["priority"],
                row["enrichment"],
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

        return [model.HomogenizationParams(row["catalog"], row["key"], row["params"]) for row in rows]

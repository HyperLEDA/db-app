from typing import Any

import pandas
import structlog

from app.data import model as data_model
from app.data import repositories
from app.domain.homogenization import model

logger: structlog.stdlib.BoundLogger = structlog.get_logger()


class Homogenization:
    def __init__(
        self,
        rules_by_column: dict[str, list[model.Rule]],
        params_by_catalog: dict[tuple[str, str], dict[str, Any]],
    ):
        self.rules_by_column = rules_by_column
        self.params_by_catalog = params_by_catalog

    def apply(self, data: pandas.DataFrame) -> list[data_model.Layer0Object]:
        result: list[data_model.Layer0Object] = []

        for _, row in data.iterrows():
            catalog_objects: dict[tuple[str, str], dict[str, Any]] = {}
            for column_name in row.index:
                if column_name not in self.rules_by_column:
                    continue

                rules = self.rules_by_column[column_name]
                value = row[column_name]

                for rule in rules:
                    key = (rule.catalog, rule.key)

                    if key not in catalog_objects:
                        catalog_objects[key] = {}

                    catalog_objects[key][rule.parameter] = value

            for key in catalog_objects:
                if key not in self.params_by_catalog:
                    continue

                catalog_objects[key].update(self.params_by_catalog[key])

            obj = data_model.Layer0Object(row[repositories.INTERNAL_ID_COLUMN_NAME], [])

            for (catalog, _), data_dict in catalog_objects.items():
                catalog_type = data_model.get_catalog_object_type(data_model.RawCatalog(catalog))

                try:
                    catalog_obj = catalog_type(**data_dict)
                except Exception as e:
                    logger.error(
                        "Error creating catalog object",
                        object_id=row[repositories.INTERNAL_ID_COLUMN_NAME],
                        error=e,
                        data_dict=data_dict,
                    )
                    continue

                obj.data.append(catalog_obj)

            result.append(obj)

        return result


def get_homogenization(
    homogenization_rules: list[model.Rule],
    homogenization_params: list[model.Params],
    table_meta: data_model.Layer0TableMeta,
) -> Homogenization:
    rules_by_column: dict[str, list[model.Rule]] = {}
    rules = []

    for rule in homogenization_rules:
        key = (rule.catalog, rule.parameter, rule.key)

        if rule.table_filters.apply(table_meta):
            rules.append(rule)

    for column in table_meta.column_descriptions:
        column_rules: dict[tuple[str, str, str], model.Rule] = {}

        for rule in rules:
            key = (rule.catalog, rule.parameter, rule.key)

            if rule.column_filters.apply(table_meta, column) and (
                key not in column_rules or rule.priority > column_rules[key].priority
            ):
                column_rules[key] = rule

        if len(column_rules) == 0:
            continue

        if column_rules:
            rules_by_column[column.name] = list(column_rules.values())

    params_by_catalog: dict[tuple[str, str], dict[str, Any]] = {}

    for param in homogenization_params:
        key = (param.catalog, param.key)

        if key not in params_by_catalog:
            params_by_catalog[key] = {}

        params_by_catalog[key].update(param.params)

    return Homogenization(rules_by_column, params_by_catalog)

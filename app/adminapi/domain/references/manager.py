import datetime
import json
from typing import Any, final

from app.adminapi import repository
from app.adminapi.domain.references import registry
from app.adminapi.repository import references
from app.lib.web.errors import ConflictError, NotFoundError, RuleValidationError
from app.specs import adminapi as spec


def _humanize_name(name: str) -> str:
    return name.replace("_", " ").strip().capitalize()


def _format_option_description(row: dict[str, Any], display: registry.ReferenceOptionDisplay) -> str | None:
    parts: list[str] = []
    for column_name in display.description_columns:
        value = row.get(column_name)
        if value is None:
            continue
        if isinstance(value, list):
            parts.append(", ".join(str(item) for item in value))
        else:
            parts.append(str(value))
    if not parts:
        return None
    return ", ".join(parts)


def _postgres_to_data_type(
    column: references.ReferenceColumnInfo,
) -> tuple[spec.ReferenceDataType, spec.ReferenceDataType | None]:
    data_type = column.data_type
    udt_name = column.udt_name

    if data_type == "ARRAY":
        element_type, _ = _postgres_udt_to_data_type(udt_name.lstrip("_"))
        return spec.ReferenceDataType.ARRAY, element_type

    result, _ = _postgres_udt_to_data_type(udt_name if data_type == "USER-DEFINED" else data_type)
    return result, None


def _postgres_udt_to_data_type(type_name: str) -> tuple[spec.ReferenceDataType, spec.ReferenceDataType | None]:
    normalized = type_name.lower()
    if normalized in {"text", "character varying", "character", "char", "name", "uuid"}:
        return spec.ReferenceDataType.STRING, None
    if normalized in {"integer", "smallint", "bigint", "int2", "int4", "int8", "serial"}:
        return spec.ReferenceDataType.INTEGER, None
    if normalized in {"double precision", "real", "numeric", "float4", "float8"}:
        return spec.ReferenceDataType.NUMBER, None
    if normalized == "boolean":
        return spec.ReferenceDataType.BOOLEAN, None
    if normalized in {"json", "jsonb"}:
        return spec.ReferenceDataType.JSON, None
    if normalized in {"timestamp without time zone", "timestamp with time zone", "date", "time without time zone"}:
        return spec.ReferenceDataType.DATETIME, None
    return spec.ReferenceDataType.STRING, None


def _input_kind_for_column(
    column: references.ReferenceColumnInfo,
    data_type: spec.ReferenceDataType,
) -> spec.ReferenceInputKind:
    if column.enum_values:
        return spec.ReferenceInputKind.SELECT
    if column.foreign_key is not None:
        return spec.ReferenceInputKind.REFERENCE
    if data_type in {spec.ReferenceDataType.NUMBER, spec.ReferenceDataType.INTEGER}:
        return spec.ReferenceInputKind.NUMBER
    if data_type in {spec.ReferenceDataType.JSON, spec.ReferenceDataType.ARRAY}:
        return spec.ReferenceInputKind.JSON
    if column.name == "description" and data_type == spec.ReferenceDataType.STRING:
        return spec.ReferenceInputKind.TEXTAREA
    return spec.ReferenceInputKind.TEXT


def _build_select_options(
    column: references.ReferenceColumnInfo,
) -> list[spec.ReferenceSelectOption]:
    return [
        spec.ReferenceSelectOption(
            value=value,
            label=value,
            description=column.enum_value_descriptions.get(value),
        )
        for value in column.enum_values
    ]


def _db_value_to_json(value: Any, data_type: spec.ReferenceDataType) -> spec.ReferenceValue:
    if value is None:
        return None
    if data_type == spec.ReferenceDataType.DATETIME and isinstance(value, datetime.datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=datetime.UTC).isoformat().replace("+00:00", "Z")
        return value.astimezone(datetime.UTC).isoformat().replace("+00:00", "Z")
    if data_type == spec.ReferenceDataType.NUMBER:
        return float(value)
    if data_type == spec.ReferenceDataType.INTEGER:
        return int(value)
    if data_type == spec.ReferenceDataType.BOOLEAN:
        return bool(value)
    if data_type == spec.ReferenceDataType.JSON:
        if isinstance(value, (dict, list)):
            return value
        if isinstance(value, str):
            return json.loads(value)
        return value
    if data_type == spec.ReferenceDataType.ARRAY:
        if isinstance(value, list):
            return value
        return list(value)
    if isinstance(value, memoryview):
        return bytes(value).decode()
    return str(value)


def _parse_json_value(value: spec.ReferenceValue, field_name: str) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise RuleValidationError(f"Field '{field_name}' must contain valid JSON") from exc
    raise RuleValidationError(f"Field '{field_name}' must contain valid JSON")


def _parse_datetime_value(value: spec.ReferenceValue, field_name: str) -> datetime.datetime:
    if not isinstance(value, str):
        raise RuleValidationError(f"Field '{field_name}' must be an ISO datetime string")
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise RuleValidationError(f"Field '{field_name}' must be an ISO datetime string") from exc
    if parsed.tzinfo is not None:
        return parsed.astimezone(datetime.UTC).replace(tzinfo=None)
    return parsed


def _parse_scalar_value(
    value: spec.ReferenceValue,
    data_type: spec.ReferenceDataType,
    field_name: str,
    *,
    nullable: bool,
) -> Any:
    if value is None:
        if nullable:
            return None
        raise RuleValidationError(f"Field '{field_name}' cannot be null")

    if data_type == spec.ReferenceDataType.STRING:
        if not isinstance(value, str):
            raise RuleValidationError(f"Field '{field_name}' must be a string")
        return value

    if data_type == spec.ReferenceDataType.INTEGER:
        if isinstance(value, bool) or not isinstance(value, int):
            raise RuleValidationError(f"Field '{field_name}' must be an integer")
        return value

    if data_type == spec.ReferenceDataType.NUMBER:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise RuleValidationError(f"Field '{field_name}' must be a number")
        return float(value)

    if data_type == spec.ReferenceDataType.BOOLEAN:
        if not isinstance(value, bool):
            raise RuleValidationError(f"Field '{field_name}' must be a boolean")
        return value

    if data_type == spec.ReferenceDataType.JSON:
        return _parse_json_value(value, field_name)

    if data_type == spec.ReferenceDataType.DATETIME:
        return _parse_datetime_value(value, field_name)

    raise RuleValidationError(f"Field '{field_name}' has unsupported data type")


def _parse_array_value(
    value: spec.ReferenceValue,
    items_data_type: spec.ReferenceDataType | None,
    field_name: str,
    *,
    nullable: bool,
) -> Any:
    if value is None:
        if nullable:
            return None
        raise RuleValidationError(f"Field '{field_name}' cannot be null")
    if not isinstance(value, list):
        raise RuleValidationError(f"Field '{field_name}' must be an array")
    if items_data_type is None:
        raise RuleValidationError(f"Field '{field_name}' has unsupported array item type")
    return [_parse_scalar_value(item, items_data_type, field_name, nullable=False) for item in value]


def _resource_descriptor(
    metadata: references.ReferenceTableInfo,
) -> spec.ReferenceResourceDescriptor:
    fields: list[spec.ReferenceFieldDescriptor] = []
    for column_name, column in metadata.columns.items():
        data_type, items_data_type = _postgres_to_data_type(column)
        input_kind = _input_kind_for_column(column, data_type)
        input_options = _build_select_options(column) if input_kind == spec.ReferenceInputKind.SELECT else None
        fields.append(
            spec.ReferenceFieldDescriptor(
                name=column_name,
                label=_humanize_name(column_name),
                description=column.description or _humanize_name(column_name),
                data_type=data_type,
                items_data_type=items_data_type,
                required=column.not_null and column.column_default is None,
                nullable=not column.not_null,
                input=spec.ReferenceInput(kind=input_kind, options=input_options),
            )
        )
    return spec.ReferenceResourceDescriptor(
        schema_name=metadata.schema,
        table=metadata.name,
        title=metadata.description or _humanize_name(metadata.name),
        description=metadata.description or _humanize_name(metadata.name),
        fields=fields,
    )


def _row_item(
    metadata: references.ReferenceTableInfo,
    row: dict[str, Any],
) -> spec.ReferenceRowItem:
    key: dict[str, spec.ReferenceValue] = {}
    payload: dict[str, spec.ReferenceValue] = {}
    for column_name, column in metadata.columns.items():
        data_type, _ = _postgres_to_data_type(column)
        json_value = _db_value_to_json(row[column_name], data_type)
        if column_name in metadata.primary_key_columns:
            key[column_name] = json_value
        else:
            payload[column_name] = json_value
    return spec.ReferenceRowItem(key=key, row=payload)


def _require_metadata(
    repo: repository.Repository,
    schema: str,
    table: str,
) -> references.ReferenceTableInfo:
    if not registry.is_allowed_reference(schema, table):
        raise NotFoundError(entity_name="reference table", entity=f"{schema}.{table}")
    metadata = repo.get_reference_table_metadata(schema, table)
    if not metadata.columns:
        raise NotFoundError(entity_name="reference table", entity=f"{schema}.{table}")
    return metadata


def _require_column(
    metadata: references.ReferenceTableInfo,
    field: str,
) -> references.ReferenceColumnInfo:
    column = metadata.columns.get(field)
    if column is None:
        raise RuleValidationError(f"Unknown field '{field}'")
    return column


def _parse_key(
    metadata: references.ReferenceTableInfo,
    key: dict[str, spec.ReferenceValue],
) -> dict[str, Any]:
    if not key:
        raise RuleValidationError("Key must not be empty")
    parsed: dict[str, Any] = {}
    for column_name in metadata.primary_key_columns:
        if column_name not in key:
            raise RuleValidationError(f"Key is missing field '{column_name}'")
        column = metadata.columns[column_name]
        data_type, items_data_type = _postgres_to_data_type(column)
        if data_type == spec.ReferenceDataType.ARRAY:
            parsed[column_name] = _parse_array_value(
                key[column_name],
                items_data_type,
                column_name,
                nullable=False,
            )
        else:
            parsed[column_name] = _parse_scalar_value(
                key[column_name],
                data_type,
                column_name,
                nullable=False,
            )
    return parsed


def _parse_row_values(
    metadata: references.ReferenceTableInfo,
    values: dict[str, spec.ReferenceValue],
    *,
    for_create: bool,
) -> dict[str, Any]:
    if not values:
        raise RuleValidationError("At least one field must be provided")

    unknown = sorted(set(values) - set(metadata.columns))
    if unknown:
        raise RuleValidationError(f"Unknown fields: {', '.join(unknown)}")

    parsed: dict[str, Any] = {}
    for column_name, raw_value in values.items():
        column = metadata.columns[column_name]
        data_type, items_data_type = _postgres_to_data_type(column)
        if data_type == spec.ReferenceDataType.ARRAY:
            parsed[column_name] = _parse_array_value(
                raw_value,
                items_data_type,
                column_name,
                nullable=not column.not_null,
            )
        else:
            parsed[column_name] = _parse_scalar_value(
                raw_value,
                data_type,
                column_name,
                nullable=not column.not_null,
            )

        if not for_create and column.is_primary_key and raw_value is None:
            raise RuleValidationError(f"Primary key field '{column_name}' cannot be null")

    return parsed


def _validate_enum_values(
    metadata: references.ReferenceTableInfo,
    values: dict[str, Any],
) -> None:
    for column_name, value in values.items():
        column = metadata.columns[column_name]
        if not column.enum_values or value is None:
            continue
        if str(value) not in column.enum_values:
            raise RuleValidationError(f"Field '{column_name}' must be one of the allowed {column.udt_name} values")


def _validate_foreign_keys(
    repo: repository.Repository,
    metadata: references.ReferenceTableInfo,
    values: dict[str, Any],
) -> None:
    for column_name, value in values.items():
        column = metadata.columns[column_name]
        if column.foreign_key is None or value is None:
            continue
        fk = column.foreign_key
        if not repo.reference_foreign_key_exists(fk.schema, fk.table, fk.column, value):
            raise RuleValidationError(f"Field '{column_name}' references missing row in '{fk.schema}.{fk.table}'")


def _validate_required_on_create(
    metadata: references.ReferenceTableInfo,
    values: dict[str, Any],
) -> None:
    for column_name, column in metadata.columns.items():
        if column.not_null and column.column_default is None and column_name not in values:
            raise RuleValidationError(f"Field '{column_name}' is required")


@final
class ReferencesManager:
    def __init__(self, repo: repository.Repository) -> None:
        self._repo = repo

    def list_references(self) -> spec.ListReferencesResponse:
        references: list[spec.ReferenceResourceDescriptor] = []
        for resource in registry.REFERENCE_RESOURCES:
            metadata = self._repo.get_reference_table_metadata(resource.schema, resource.table)
            references.append(_resource_descriptor(metadata))
        return spec.ListReferencesResponse(references=references)

    def list_rows(
        self,
        schema: str,
        table: str,
        request: spec.ListReferenceRowsRequest,
    ) -> spec.ListReferenceRowsResponse:
        metadata = _require_metadata(self._repo, schema, table)
        column_names = list(metadata.columns)
        rows_data = self._repo.list_reference_rows(
            schema,
            table,
            request.query,
            column_names,
            metadata.primary_key_columns,
            request.page,
            request.page_size,
        )
        total = self._repo.count_reference_rows(schema, table, request.query, column_names)
        items = [_row_item(metadata, row) for row in rows_data]
        return spec.ListReferenceRowsResponse(
            schema_name=schema,
            table=table,
            items=items,
            page=request.page,
            page_size=request.page_size,
            total=total,
        )

    def list_field_options(
        self,
        schema: str,
        table: str,
        field: str,
        request: spec.ListReferenceFieldOptionsRequest,
    ) -> spec.ListReferenceFieldOptionsResponse:
        metadata = _require_metadata(self._repo, schema, table)
        column = _require_column(metadata, field)
        if column.foreign_key is None:
            raise RuleValidationError(f"Field '{field}' does not support options")

        target_schema = column.foreign_key.schema
        target_table = column.foreign_key.table
        if not registry.is_allowed_reference(target_schema, target_table):
            raise RuleValidationError(f"Referenced table '{target_schema}.{target_table}' is not available")

        target_metadata = self._repo.get_reference_table_metadata(target_schema, target_table)
        display = registry.REFERENCE_OPTION_DISPLAY.get(
            (target_schema, target_table),
            registry.ReferenceOptionDisplay(label_column=target_metadata.primary_key_columns[0]),
        )
        if display.label_column not in target_metadata.columns:
            raise RuleValidationError(f"Option label column '{display.label_column}' was not found")

        column_names = list(target_metadata.columns)
        rows_data = self._repo.list_reference_options(
            target_schema,
            target_table,
            request.query,
            column_names,
            target_metadata.primary_key_columns,
            request.page,
            request.page_size,
        )
        total = self._repo.count_reference_options(
            target_schema,
            target_table,
            request.query,
            column_names,
        )
        value_column = column.foreign_key.column
        value_data_type = _postgres_to_data_type(target_metadata.columns[value_column])[0]
        items = [
            spec.ReferenceFieldOption(
                value=_db_value_to_json(row[value_column], value_data_type),
                label=str(row.get(display.label_column) or row[value_column]),
                description=_format_option_description(row, display),
            )
            for row in rows_data
        ]
        return spec.ListReferenceFieldOptionsResponse(
            field=field,
            items=items,
            page=request.page,
            page_size=request.page_size,
            total=total,
        )

    def create_row(
        self,
        schema: str,
        table: str,
        request: spec.CreateReferenceRowRequest,
    ) -> spec.CreateReferenceRowResponse:
        metadata = _require_metadata(self._repo, schema, table)
        parsed_values = _parse_row_values(metadata, request.row, for_create=True)
        _validate_enum_values(metadata, parsed_values)
        _validate_foreign_keys(self._repo, metadata, parsed_values)
        _validate_required_on_create(metadata, parsed_values)
        try:
            with self._repo.with_tx():
                self._repo.insert_reference_row(schema, table, parsed_values)
        except Exception as exc:
            if references.ReferencesRepository.is_unique_violation(exc):
                raise ConflictError("A row with the same unique key already exists") from exc
            raise
        return spec.CreateReferenceRowResponse()

    def patch_row(
        self,
        schema: str,
        table: str,
        request: spec.PatchReferenceRowRequest,
    ) -> spec.PatchReferenceRowResponse:
        metadata = _require_metadata(self._repo, schema, table)
        key = _parse_key(metadata, request.key)
        if self._repo.get_reference_row_by_key(schema, table, metadata.primary_key_columns, key) is None:
            raise NotFoundError(entity_name="reference row", entity=json.dumps(key))

        if not request.changes:
            return spec.PatchReferenceRowResponse()

        parsed_changes = _parse_row_values(metadata, request.changes, for_create=False)
        _validate_enum_values(metadata, parsed_changes)
        _validate_foreign_keys(self._repo, metadata, parsed_changes)
        try:
            with self._repo.with_tx():
                updated = self._repo.update_reference_row(
                    schema,
                    table,
                    metadata.primary_key_columns,
                    key,
                    parsed_changes,
                )
        except Exception as exc:
            if references.ReferencesRepository.is_unique_violation(exc):
                raise ConflictError("A row with the same unique key already exists") from exc
            raise

        if updated == 0:
            raise NotFoundError(entity_name="reference row", entity=json.dumps(key))
        return spec.PatchReferenceRowResponse()

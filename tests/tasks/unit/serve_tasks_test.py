from app.catalogs import layer1
from app.specs import adminapi as spec
from app.tasks import flows


def test_schedules_and_structured_upload_deployments() -> None:
    assert flows.schedule_env_var("layer2-import") == "TASK_SCHEDULE_LAYER2_IMPORT"
    assert flows.schedule_env_var("layer2-import-objects") == "TASK_SCHEDULE_LAYER2_IMPORT_OBJECTS"
    assert flows.cron_from_env("layer2-import", {}) is None
    assert flows.cron_from_env("layer2-import", {"TASK_SCHEDULE_LAYER2_IMPORT": ""}) is None
    assert flows.cron_from_env("layer2-import", {"TASK_SCHEDULE_LAYER2_IMPORT": "  "}) is None
    assert flows.cron_from_env("layer2-import", {"TASK_SCHEDULE_LAYER2_IMPORT": "0 12 * * *"}) == "0 12 * * *"

    by_name = {
        d.name: d
        for d in flows.build_deployments(
            {"TASK_SCHEDULE_LAYER2_IMPORT": "0 12 * * *", "TASK_SCHEDULE_LAYER2_IMPORT_OBJECTS": "0 0 * * 0"}
        )
    }
    assert len(by_name["layer2-import"].schedules or []) == 1
    assert len(by_name["layer2-import-objects"].schedules or []) == 1
    assert len(by_name["layer2-import-redshift"].schedules or []) == 0
    for catalog in layer1.Catalog:
        assert callable(getattr(flows, f"structured_upload_{catalog.value}"))

    schema = spec.CatalogSchema(
        catalog="icrs",
        title="ICRS",
        description="positions",
        fields=[
            spec.CatalogField(
                name="ra",
                data_type=spec.DatatypeEnum["float"],
                unit="deg",
                required=True,
                description="Right ascension",
            )
        ],
    )
    upload = next(
        item
        for item in flows.build_deployments({"TASK_SCHEDULE_UPLOAD_ICRS": "0 * * * *"}, catalog_schemas=[schema])
        if item.name == "upload-icrs"
    )
    assert upload.entrypoint is not None and upload.entrypoint.endswith("structured_upload_icrs")
    assert len(upload.schedules or []) == 1
    rendered = str(upload._parameter_openapi_schema.model_dump())  # noqa: SLF001
    assert "ra" in rendered and "table_name" in rendered and "batch_size" in rendered and "row_filter" in rendered

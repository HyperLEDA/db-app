from app.catalogs import layer1
from app.specs import adminapi as spec
from app.tasks import flows


def test_schedule_env_var_names() -> None:
    assert flows.schedule_env_var("layer2-import") == "TASK_SCHEDULE_LAYER2_IMPORT"
    assert flows.schedule_env_var("layer2-import-designation") == "TASK_SCHEDULE_LAYER2_IMPORT_DESIGNATION"


def test_cron_from_env_empty_means_none() -> None:
    assert flows.cron_from_env("layer2-import", {}) is None
    assert flows.cron_from_env("layer2-import", {"TASK_SCHEDULE_LAYER2_IMPORT": ""}) is None
    assert flows.cron_from_env("layer2-import", {"TASK_SCHEDULE_LAYER2_IMPORT": "  "}) is None


def test_cron_from_env_reads_expression() -> None:
    assert flows.cron_from_env("layer2-import", {"TASK_SCHEDULE_LAYER2_IMPORT": "0 12 * * *"}) == "0 12 * * *"


def test_build_deployments_applies_cron() -> None:
    deployments = flows.build_deployments(
        {
            "TASK_SCHEDULE_LAYER2_IMPORT": "0 12 * * *",
            "TASK_SCHEDULE_LAYER2_IMPORT_ICRS": "0 0 * * 0",
        }
    )
    by_name = {d.name: d for d in deployments}
    assert len(by_name["layer2-import"].schedules or []) == 1
    assert len(by_name["layer2-import-icrs"].schedules or []) == 1
    assert len(by_name["layer2-import-designation"].schedules or []) == 0


def test_structured_upload_flows_are_importable() -> None:
    for catalog in layer1.Catalog:
        assert callable(getattr(flows, f"structured_upload_{catalog.value}"))


def test_upload_deployment_exposes_column_schema() -> None:
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
    deployments = flows.build_deployments(
        {"TASK_SCHEDULE_UPLOAD_ICRS": "0 * * * *"},
        catalog_schemas=[schema],
    )
    upload = next(item for item in deployments if item.name == "upload-icrs")
    assert upload.entrypoint is not None
    assert upload.entrypoint.endswith("structured_upload_icrs")
    assert len(upload.schedules or []) == 1
    dumped = upload._parameter_openapi_schema.model_dump()  # noqa: SLF001
    rendered = str(dumped)
    assert "ra" in rendered
    assert "table_name" in rendered
    assert "batch_size" in rendered

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


def test_build_deployments_without_schedules() -> None:
    deployments = flows.build_deployments({})
    assert len(deployments) == 6
    assert [d.name for d in deployments] == list(flows.LAYER2_TASK_NAMES)
    assert "layer2-orphan-cleanup" in [d.name for d in deployments]
    for deployment in deployments:
        assert len(deployment.schedules or []) == 0


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

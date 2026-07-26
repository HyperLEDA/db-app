import unittest

from app.commands.serve_tasks import flows


class ServeTasksTest(unittest.TestCase):
    def test_schedule_env_var_names(self) -> None:
        self.assertEqual(flows.schedule_env_var("layer2-import"), "TASK_SCHEDULE_LAYER2_IMPORT")
        self.assertEqual(
            flows.schedule_env_var("layer2-import-designation"),
            "TASK_SCHEDULE_LAYER2_IMPORT_DESIGNATION",
        )

    def test_cron_from_env_empty_means_none(self) -> None:
        self.assertIsNone(flows.cron_from_env("layer2-import", {}))
        self.assertIsNone(flows.cron_from_env("layer2-import", {"TASK_SCHEDULE_LAYER2_IMPORT": ""}))
        self.assertIsNone(flows.cron_from_env("layer2-import", {"TASK_SCHEDULE_LAYER2_IMPORT": "  "}))

    def test_cron_from_env_reads_expression(self) -> None:
        self.assertEqual(
            flows.cron_from_env("layer2-import", {"TASK_SCHEDULE_LAYER2_IMPORT": "0 12 * * *"}),
            "0 12 * * *",
        )

    def test_build_deployments_without_schedules(self) -> None:
        deployments = flows.build_deployments({})
        self.assertEqual(len(deployments), 6)
        self.assertEqual(
            [d.name for d in deployments],
            list(flows.LAYER2_TASK_NAMES),
        )
        self.assertIn("layer2-orphan-cleanup", [d.name for d in deployments])
        for deployment in deployments:
            self.assertEqual(len(deployment.schedules or []), 0)

    def test_build_deployments_applies_cron(self) -> None:
        deployments = flows.build_deployments(
            {
                "TASK_SCHEDULE_LAYER2_IMPORT": "0 12 * * *",
                "TASK_SCHEDULE_LAYER2_IMPORT_ICRS": "0 0 * * 0",
            }
        )
        by_name = {d.name: d for d in deployments}
        self.assertEqual(len(by_name["layer2-import"].schedules or []), 1)
        self.assertEqual(len(by_name["layer2-import-icrs"].schedules or []), 1)
        self.assertEqual(len(by_name["layer2-import-designation"].schedules or []), 0)

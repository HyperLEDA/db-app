import unittest

import rq
import structlog

from app.data import repositories
from app.domain import model, usecases
from app.lib import testing


class QueueTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pg_storage = testing.get_or_create_test_postgres_storage()
        cls.redis_queue = testing.get_or_create_test_redis_storage()

        logger = structlog.get_logger()

        cls.actions = usecases.Actions(
            common_repo=repositories.CommonRepository(cls.pg_storage.get_storage(), logger),
            layer0_repo=repositories.Layer0Repository(cls.pg_storage.get_storage(), logger),
            layer1_repo=repositories.Layer1Repository(cls.pg_storage.get_storage(), logger),
            queue_repo=repositories.QueueRepository(cls.redis_queue.get_storage(), cls.pg_storage.config, logger),
            storage_config=cls.pg_storage.get_storage().get_config(),
            logger=logger,
        )

    def tearDown(self):
        self.redis_queue.clear()
        self.pg_storage.clear()

    def test_task_run_no_worker(self):
        response = self.actions.start_task(model.StartTaskRequest("echo", {"sleep_time_seconds": 0.2}))
        info = self.actions.get_task_info(model.GetTaskInfoRequest(response.id))

        self.assertEqual(info.id, response.id)
        self.assertEqual(info.status, "new")
        self.assertEqual(info.task_name, "echo")
        self.assertIsNone(info.start_time)
        self.assertIsNone(info.end_time)

    def test_task_run_nonexistent_task(self):
        with self.assertRaises(Exception):
            self.actions.start_task(model.StartTaskRequest("absolutely_real_task", {}))

    def test_task_run_success(self):
        response = self.actions.start_task(model.StartTaskRequest("echo", {"sleep_time_seconds": 0.2}))

        worker = rq.Worker("test_queue", connection=self.redis_queue.get_storage().get_connection())
        worker.work(burst=True)

        info = self.actions.get_task_info(model.GetTaskInfoRequest(response.id))
        self.assertEqual(info.id, response.id)
        self.assertEqual(info.status, "done")
        self.assertEqual(info.task_name, "echo")
        self.assertIsNotNone(info.start_time)
        self.assertIsNotNone(info.end_time)

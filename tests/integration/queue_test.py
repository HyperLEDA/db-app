import unittest
from concurrent import futures

import rq
import structlog

from app import schema
from app.commands.adminapi import depot
from app.data import repositories
from app.domain import actions
from app.lib import testing


class QueueTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with futures.ThreadPoolExecutor() as group:
            pg_thread = group.submit(testing.get_test_postgres_storage)
            redis_thread = group.submit(testing.get_test_redis_storage)

        cls.pg_storage = pg_thread.result()
        cls.redis_queue = redis_thread.result()

        logger = structlog.get_logger()

        cls.depot = depot.get_mock_depot()
        cls.depot.common_repo = repositories.CommonRepository(cls.pg_storage.get_storage(), logger)
        cls.depot.layer0_repo = repositories.Layer0Repository(cls.pg_storage.get_storage(), logger)
        cls.depot.queue_repo = repositories.QueueRepository(
            cls.redis_queue.get_storage(), cls.pg_storage.config, logger
        )

    def tearDown(self):
        self.redis_queue.clear()
        self.pg_storage.clear()

    def test_task_run_no_worker(self):
        response = actions.start_task(self.depot, schema.StartTaskRequest("echo", {"sleep_time_seconds": 0.2}))
        info = actions.get_task_info(self.depot, schema.GetTaskInfoRequest(response.id))

        self.assertEqual(info.id, response.id)
        self.assertEqual(info.status, "new")
        self.assertEqual(info.task_name, "echo")
        self.assertIsNone(info.start_time)
        self.assertIsNone(info.end_time)

    def test_task_run_nonexistent_task(self):
        with self.assertRaises(Exception):
            actions.start_task(self.depot, schema.StartTaskRequest("absolutely_real_task", {}))

    def test_task_run_success(self):
        response = actions.start_task(self.depot, schema.StartTaskRequest("echo", {"sleep_time_seconds": 0.2}))

        worker = rq.Worker("test_queue", connection=self.redis_queue.get_storage().get_connection())
        worker.work(burst=True)

        info = actions.get_task_info(self.depot, schema.GetTaskInfoRequest(response.id))
        self.assertEqual(info.id, response.id)
        self.assertEqual(info.status, "done")
        self.assertEqual(info.task_name, "echo")
        self.assertIsNotNone(info.start_time)
        self.assertIsNotNone(info.end_time)

import unittest
from concurrent import futures

import rq
import structlog

from app.data import repositories
from app.domain import adminapi as domain
from app.lib import testing
from app.presentation import adminapi as presentation


class QueueTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with futures.ThreadPoolExecutor() as group:
            pg_thread = group.submit(testing.get_test_postgres_storage)
            redis_thread = group.submit(testing.get_test_redis_storage)

        cls.pg_storage = pg_thread.result()
        cls.redis_queue = redis_thread.result()

        logger = structlog.get_logger()

        cls.manager = domain.TaskManager(
            repositories.CommonRepository(cls.pg_storage.get_storage(), logger),
            repositories.QueueRepository(cls.redis_queue.get_storage(), cls.pg_storage.config, logger),
        )

    def tearDown(self):
        self.redis_queue.clear()
        self.pg_storage.clear()

    def test_task_run_no_worker(self):
        response = self.manager.start_task(presentation.StartTaskRequest("echo", {"sleep_time_seconds": 0.2}))
        info = self.manager.get_task_info(presentation.GetTaskInfoRequest(response.id))

        self.assertEqual(info.id, response.id)
        self.assertEqual(info.status, "new")
        self.assertEqual(info.task_name, "echo")
        self.assertIsNone(info.start_time)
        self.assertIsNone(info.end_time)

    def test_task_run_nonexistent_task(self):
        with self.assertRaises(Exception):
            self.manager.start_task(presentation.StartTaskRequest("absolutely_real_task", {}))

    def test_task_run_success(self):
        response = self.manager.start_task(presentation.StartTaskRequest("echo", {"sleep_time_seconds": 0.2}))

        worker = rq.Worker("test_queue", connection=self.redis_queue.get_storage().get_connection())
        worker.work(burst=True)

        info = self.manager.get_task_info(presentation.GetTaskInfoRequest(response.id))
        self.assertEqual(info.id, response.id)
        self.assertEqual(info.status, "done")
        self.assertEqual(info.task_name, "echo")
        self.assertIsNotNone(info.start_time)
        self.assertIsNotNone(info.end_time)

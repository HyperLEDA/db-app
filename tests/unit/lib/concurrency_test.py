import time
import unittest

from app.lib.concurrency import ErrorGroup


class ErrorGroupTest(unittest.TestCase):
    def test_two_run_calls_successful_wait(self):
        results = []

        def task1():
            time.sleep(0.1)
            results.append("task1")

        def task2():
            time.sleep(0.1)
            results.append("task2")

        eg = ErrorGroup()
        eg.run(task1)
        eg.run(task2)
        eg.wait()

        self.assertEqual(len(results), 2)
        self.assertIn("task1", results)
        self.assertIn("task2", results)

    def test_first_task_fails_before_second_finishes(self):
        results = []

        def failing_task():
            time.sleep(0.05)
            raise ValueError("First task failed")

        def second_task():
            time.sleep(0.2)
            results.append("second_task")

        eg = ErrorGroup()
        eg.run(failing_task)
        eg.run(second_task)

        with self.assertRaises(ValueError) as context:
            eg.wait()

        self.assertEqual(str(context.exception), "First task failed")
        self.assertEqual(len(results), 0)

    def test_first_task_fails_after_second_finishes(self):
        results = []

        def failing_task():
            time.sleep(0.2)
            raise ValueError("First task failed")

        def second_task():
            time.sleep(0.05)
            results.append("second_task")

        eg = ErrorGroup()
        eg.run(failing_task)
        eg.run(second_task)

        with self.assertRaises(ValueError) as context:
            eg.wait()

        self.assertEqual(str(context.exception), "First task failed")
        self.assertEqual(len(results), 1)
        self.assertIn("second_task", results)

    def test_empty_errorgroup_wait(self):
        eg = ErrorGroup()
        eg.wait()

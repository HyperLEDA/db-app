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

    def test_incorrect_args_number(self):
        results = []

        def failing_task(arg1):
            print(arg1)

        def second_task():
            time.sleep(0.05)
            results.append("second_task")

        eg = ErrorGroup()
        eg.run(failing_task)  # pyright: ignore[reportCallIssue] - this is intentional
        eg.run(second_task)

        with self.assertRaises(TypeError) as context:
            eg.wait()

        self.assertIn("missing 1 required positional argument", str(context.exception))

    def test_multiple_tasks_with_return_values(self):
        def task1():
            time.sleep(0.1)
            return "result1"

        def task2():
            time.sleep(0.1)
            return "result2"

        eg = ErrorGroup()
        result1 = eg.run(task1)
        result2 = eg.run(task2)

        eg.wait()

        self.assertEqual(result1.result(), "result1")
        self.assertEqual(result2.result(), "result2")

    def test_result_called_after_error(self):
        def task1() -> int:
            return 123

        def task2() -> str:
            raise RuntimeError("fail")

        eg = ErrorGroup()
        result1 = eg.run(task1)
        result2 = eg.run(task2)

        with self.assertRaises(RuntimeError):
            eg.wait()

        self.assertEqual(result1.result(), 123)
        with self.assertRaises(RuntimeError):
            result2.result()

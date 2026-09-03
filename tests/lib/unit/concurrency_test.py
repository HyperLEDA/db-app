import time

import pytest

from app.lib.concurrency import ErrorGroup


def test_two_run_calls_successful_wait() -> None:
    results: list[str] = []

    def task1() -> None:
        time.sleep(0.1)
        results.append("task1")

    def task2() -> None:
        time.sleep(0.1)
        results.append("task2")

    eg = ErrorGroup()
    eg.run(task1)
    eg.run(task2)
    eg.wait()

    assert len(results) == 2
    assert "task1" in results
    assert "task2" in results


def test_first_task_fails_after_second_finishes() -> None:
    results: list[str] = []

    def failing_task() -> None:
        time.sleep(0.2)
        raise ValueError("First task failed")

    def second_task() -> None:
        time.sleep(0.05)
        results.append("second_task")

    eg = ErrorGroup()
    eg.run(failing_task)
    eg.run(second_task)

    with pytest.raises(ValueError, match="First task failed"):
        eg.wait()

    assert len(results) == 1
    assert "second_task" in results


def test_empty_errorgroup_wait() -> None:
    eg = ErrorGroup()
    eg.wait()


def test_incorrect_args_number() -> None:
    results: list[str] = []

    def failing_task(arg1: str) -> None:
        print(arg1)

    def second_task() -> None:
        time.sleep(0.05)
        results.append("second_task")

    eg = ErrorGroup()
    eg.run(failing_task)  # pyright: ignore[reportCallIssue] - this is intentional
    eg.run(second_task)

    with pytest.raises(TypeError, match="missing 1 required positional argument"):
        eg.wait()


def test_multiple_tasks_with_return_values() -> None:
    def task1() -> str:
        time.sleep(0.1)
        return "result1"

    def task2() -> str:
        time.sleep(0.1)
        return "result2"

    eg = ErrorGroup()
    result1 = eg.run(task1)
    result2 = eg.run(task2)

    eg.wait()

    assert result1.result() == "result1"
    assert result2.result() == "result2"


def test_result_called_after_error() -> None:
    def task1() -> int:
        return 123

    def task2() -> str:
        raise RuntimeError("fail")

    eg = ErrorGroup()
    result1 = eg.run(task1)
    result2 = eg.run(task2)

    with pytest.raises(RuntimeError):
        eg.wait()

    assert result1.result() == 123
    with pytest.raises(RuntimeError):
        result2.result()

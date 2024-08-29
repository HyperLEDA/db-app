import abc
from typing import Any

import psycopg

from app import entities
from app.data.interface import transactional
from app.lib.storage import enums


class CommonRepository(transactional.Transactional):
    @abc.abstractmethod
    def create_bibliography(
        self, code: str, year: int, authors: list[str], title: str, tx: psycopg.Transaction | None = None
    ) -> int:
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def get_source_entry(self, source_name: str, tx: psycopg.Transaction | None = None) -> entities.Bibliography:
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def get_source_by_id(self, source_id: int, tx: psycopg.Transaction | None = None) -> entities.Bibliography:
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def insert_task(self, task: entities.Task, tx: psycopg.Transaction | None = None) -> int:
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def get_task_info(self, task_id: int, tx: psycopg.Transaction | None = None) -> entities.Task:
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def set_task_status(
        self, task_id: int, task_status: enums.TaskStatus, tx: psycopg.Transaction | None = None
    ) -> None:
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def fail_task(self, task_id: int, message: dict[str, Any], tx: psycopg.Transaction | None = None) -> None:
        raise NotImplementedError("not implemented")

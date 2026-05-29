import hashlib

from app.data.repositories import private as private_repo


def run_id(user_id: int, method: str, action_description: str) -> str:
    return hashlib.sha256(f"{user_id}\x00{method}\x00{action_description}".encode()).hexdigest()


class AuditManager:
    def __init__(self, repository: private_repo.PrivateRepository) -> None:
        self._repository = repository

    def record_action(self, user_id: int, method: str, action_description: str | None) -> None:
        resolved_run_id = run_id(user_id, method, action_description) if action_description is not None else None
        self._repository.record_action(user_id, method, action_description, resolved_run_id)

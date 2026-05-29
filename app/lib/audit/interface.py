import abc


class ActionRecorder(abc.ABC):
    @abc.abstractmethod
    def record_action(self, user_id: int, method: str, action_description: str | None) -> None: ...

import abc


class ActionRecorder(abc.ABC):
    @abc.abstractmethod
    def record_action(
        self,
        username: str,
        method: str,
        action_description: str | None,
        request: dict[str, object] | None,
    ) -> None: ...

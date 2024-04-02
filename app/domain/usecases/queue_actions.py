import structlog


class QueueActions:
    def __init__(self, logger: structlog.BoundLogger) -> None:
        self._logger = logger

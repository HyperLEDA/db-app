import structlog

PROCESSORS: list[structlog.types.Processor] = [
    structlog.contextvars.merge_contextvars,
    structlog.processors.add_log_level,
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.JSONRenderer(),
]


def configure(log_level: str | int) -> None:
    structlog.configure(
        processors=PROCESSORS,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
    )

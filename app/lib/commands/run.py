import structlog

from app.lib.commands import interface


def run(command: interface.Command):
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.dev.ConsoleRenderer(),
        ],
    )

    logger: structlog.stdlib.BoundLogger = structlog.get_logger()

    try:
        command.prepare()
    except Exception as e:
        logger.error("Error during preparation", exc_info=e)
        _cleanup(logger, command)
        raise e

    try:
        command.run()
    except Exception as e:
        logger.error("Error during execution", exc_info=e)
        _cleanup(logger, command)
        raise e

    _cleanup(logger, command)


def _cleanup(logger: structlog.stdlib.BoundLogger, command: interface.Command):
    try:
        command.cleanup()
    except Exception as e:
        logger.error("Error during cleanup", exc_info=e)
        raise e

import os

import structlog

from app.lib.commands import interface


def run(command: interface.Command):
    log_level = os.getenv("LOG_LEVEL", "info")

    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(log_level))

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

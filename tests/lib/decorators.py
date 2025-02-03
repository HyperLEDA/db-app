import functools
import pathlib

import requests


def test_logging_decorator(func, source_file: str):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        prefix = f"\033[94m[{pathlib.Path(source_file).stem}]\x1b[0m \x1b[31;20m[{func.__name__}]\x1b[0m"

        print(f"{prefix} Start")
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            print(f"{prefix} Error: {e}")
            raise KeyboardInterrupt from e

        print(f"{prefix} Finish")
        return result

    return wrapper


def test_status_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)

        if isinstance(result, requests.Response):
            if result.status_code != 200:
                raise RuntimeError(f"Status code: {result.status_code}, {result.json()}")

        return result

    return wrapper

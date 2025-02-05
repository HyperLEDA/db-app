import functools
import pathlib


def test_logging_decorator(source_file: str):
    def decorator(func):
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

    return decorator

import functools
import pathlib
import time


def test_logging_decorator(source_file: str):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            prefix = f"\033[94m[{pathlib.Path(source_file).stem}]\x1b[0m \x1b[31;20m[{func.__name__}]\x1b[0m"

            print(f"{prefix} Start")
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                elapsed_time = (time.time() - start_time) * 1000
                print(f"{prefix} \x1b[32m[{elapsed_time:0.0f}ms]\x1b[0m Error: {e}")
                raise KeyboardInterrupt from e

            elapsed_time = (time.time() - start_time) * 1000
            print(f"{prefix} \x1b[32m[{elapsed_time:0.0f}ms]\x1b[0m Finish")
            return result

        return wrapper

    return decorator

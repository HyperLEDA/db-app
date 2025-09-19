import functools
import time

from tests.lib import colors


def test_logging_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        func_name = func.__name__.replace("_", " ")
        colored_func = colors.color(func_name, "red")

        print(f"    [{colors.color('S', 'orange')}] {colored_func}")
        start_time = time.time()

        exception = None
        try:
            result = func(*args, **kwargs)
            status = "F"
        except Exception as e:
            exception = e
            status = "E"
            raise KeyboardInterrupt from e
        finally:
            elapsed_time = (time.time() - start_time) * 1000
            colored_time = colors.color(f"{elapsed_time:0.0f}ms", "green")
            print(f"    [{colors.color(status, 'orange')}] {colored_func} [{colored_time}]")

            if status == "E" and exception:
                print(f"    {type(exception).__name__}: {exception}")

        return result

    return wrapper

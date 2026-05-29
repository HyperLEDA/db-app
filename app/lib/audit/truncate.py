_TRUNCATED_ARRAY = "<truncated array>"
_TRUNCATED_DICT = "<truncated dictionary>"


def _is_primitive(value: object) -> bool:
    return value is None or isinstance(value, (bool, int, float, str))


def truncate_request(body: dict[str, object]) -> dict[str, object]:
    return {key: _truncate_value(value, depth=0) for key, value in body.items()}


def _truncate_value(value: object, depth: int) -> object:
    if _is_primitive(value):
        return value
    if isinstance(value, list):
        return _TRUNCATED_ARRAY
    if isinstance(value, dict):
        if depth == 0:
            return {key: _truncate_value(nested, depth=1) for key, nested in value.items()}
        return _TRUNCATED_DICT
    return str(value)

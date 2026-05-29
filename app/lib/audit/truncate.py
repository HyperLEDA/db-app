_MAX_DICT_DEPTH = 5
_MIN_TRUNCATE_LIST_SIZE = 5

_TRUNCATED_ARRAY = "<truncated array>"
_TRUNCATED_DICT = "<truncated dictionary>"


def _is_primitive(value: object) -> bool:
    return value is None or isinstance(value, (bool, int, float, str))


def truncate_request(body: dict[str, object]) -> dict[str, object]:
    return {key: _truncate_value(value, dict_layer=1) for key, value in body.items()}


def _truncate_value(value: object, dict_layer: int) -> object:
    if _is_primitive(value):
        return value
    if isinstance(value, list):
        if len(value) < _MIN_TRUNCATE_LIST_SIZE:
            return [_truncate_value(item, dict_layer=dict_layer) for item in value]
        return _TRUNCATED_ARRAY
    if isinstance(value, dict):
        next_layer = dict_layer + 1
        if next_layer > _MAX_DICT_DEPTH:
            return _TRUNCATED_DICT
        return {key: _truncate_value(nested, dict_layer=next_layer) for key, nested in value.items()}
    return str(value)

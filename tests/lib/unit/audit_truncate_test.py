import unittest

from app.lib.audit import truncate


class AuditTruncateTest(unittest.TestCase):
    def test_keeps_shallow_structures(self) -> None:
        body = {
            "data": {
                "value1": "string",
                "value2": ["string1", "string2"],
                "nested": {"value": "string"},
            },
            "root_int": 123,
            "list_key": [12, 34, 56],
        }
        self.assertEqual(truncate.truncate_request(body), body)

    def test_keeps_root_level_primitives(self) -> None:
        body = {"flag": True, "count": 0, "label": None}
        self.assertEqual(truncate.truncate_request(body), body)

    def test_truncates_long_lists(self) -> None:
        body = {"items": [1, 2, 3, 4, 5]}
        self.assertEqual(truncate.truncate_request(body), {"items": "<truncated array>"})

    def test_truncates_deep_dictionaries(self) -> None:
        body: dict[str, object] = {"level1": {}}
        current = body["level1"]
        assert isinstance(current, dict)
        for _ in range(4):
            current["nested"] = {}
            current = current["nested"]
            assert isinstance(current, dict)
        current["value"] = "deep"

        self.assertEqual(
            truncate.truncate_request(body),
            {
                "level1": {
                    "nested": {
                        "nested": {
                            "nested": {
                                "nested": "<truncated dictionary>",
                            },
                        },
                    },
                },
            },
        )

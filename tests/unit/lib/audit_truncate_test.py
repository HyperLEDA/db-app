import unittest

from app.lib.audit import truncate


class AuditTruncateTest(unittest.TestCase):
    def test_truncates_nested_structures_beyond_second_level(self) -> None:
        body = {
            "data": {
                "value1": "string",
                "value2": ["string1", "string2"],
                "nested": {"value": "string"},
            },
            "root_int": 123,
            "list_key": [12, 34, 56],
        }
        self.assertEqual(
            truncate.truncate_request(body),
            {
                "data": {
                    "value1": "string",
                    "value2": "<truncated array>",
                    "nested": "<truncated dictionary>",
                },
                "root_int": 123,
                "list_key": "<truncated array>",
            },
        )

    def test_keeps_root_level_primitives(self) -> None:
        body = {"flag": True, "count": 0, "label": None}
        self.assertEqual(truncate.truncate_request(body), body)

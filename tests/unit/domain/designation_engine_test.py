import unittest

from app.domain.designation.engine import Rule, RuleEngine, TransformOp, TransformSpec


class DesignationEngineTest(unittest.TestCase):
    def test_empty_input(self) -> None:
        engine = RuleEngine.compile([])
        self.assertIsNone(engine.format(""))
        self.assertIsNone(engine.format("   "))

    def test_simple_template(self) -> None:
        engine = RuleEngine.compile(
            [
                Rule(
                    id="pgc",
                    priority=1,
                    pattern=r"^pgc\s*(\d+)$",
                    template="PGC {0}",
                )
            ]
        )
        result = engine.format("pgc 1234")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.formatted, "PGC 1234")
        self.assertEqual(result.rule_id, "pgc")

    def test_transforms(self) -> None:
        engine = RuleEngine.compile(
            [
                Rule(
                    id="ngc",
                    priority=1,
                    pattern=r"^ngc\s*0*(\d{1,4})\s*([A-Z]?)$",
                    template="NGC {0}{1}",
                    transforms={
                        1: [TransformSpec(TransformOp.STRIP_ZEROS)],
                        2: [TransformSpec(TransformOp.UPPER)],
                    },
                )
            ]
        )
        result = engine.format("ngc 0224")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.formatted, "NGC 224")

    def test_validate_rule_examples(self) -> None:
        rule = Rule(
            id="test",
            priority=1,
            pattern=r"^test\s*(\d+)$",
            template="TEST {0}",
            examples=[("test 1", "TEST 1")],
        )
        RuleEngine.compile([rule]).validate_rule(rule)

    def test_validate_rule_rejects_bad_example(self) -> None:
        rule = Rule(
            id="test",
            priority=1,
            pattern=r"^test\s*(\d+)$",
            template="TEST {0}",
            examples=[("test 1", "WRONG")],
        )
        with self.assertRaises(ValueError):
            RuleEngine.compile([rule]).validate_rule(rule)

    def test_first_match_wins(self) -> None:
        engine = RuleEngine.compile(
            [
                Rule(id="a", priority=1, pattern=r"^X(\d+)$", template="A {0}"),
                Rule(id="b", priority=2, pattern=r"^X(\d+)$", template="B {0}"),
            ]
        )
        result = engine.format("X1")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.rule_id, "a")

import unittest

from app.domain.usecases import Actions

# class VizierStub:


class SearchCatalogsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.actions = Actions(None)

    def test_run(self):
        pass

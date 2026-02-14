import unittest

from src.utils.worker import make_summary_data


class TestWorkerResultSchema(unittest.TestCase):
    def test_make_summary_data_has_required_keys(self) -> None:
        data = make_summary_data(cancelled=False, success_count=3, fail_count=1)
        self.assertEqual(data["cancelled"], False)
        self.assertEqual(data["success_count"], 3)
        self.assertEqual(data["fail_count"], 1)

    def test_make_summary_data_merges_extra(self) -> None:
        data = make_summary_data(cancelled=True, success_count=0, fail_count=0, foo="bar")
        self.assertEqual(data["foo"], "bar")


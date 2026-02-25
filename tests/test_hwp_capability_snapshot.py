import unittest

from src.core.hwp_handler import HwpHandler
from src.core.capability_mapper import CapabilityMapper


class TestHwpCapabilitySnapshot(unittest.TestCase):
    def test_introspect_capabilities_schema(self) -> None:
        snapshot = HwpHandler.introspect_capabilities()

        self.assertIsInstance(snapshot.pyhwpx_version, str)
        self.assertIsInstance(snapshot.method_count, int)
        self.assertIsInstance(snapshot.methods, list)
        self.assertIsInstance(snapshot.categories, dict)
        self.assertIn("file_io", snapshot.categories)
        self.assertIn("security_privacy", snapshot.categories)
        self.assertGreaterEqual(snapshot.method_count, 0)
        self.assertEqual(snapshot.method_count, len(snapshot.methods))

    def test_capability_mapper_returns_coverage_result(self) -> None:
        snapshot = HwpHandler.introspect_capabilities()
        mapper = CapabilityMapper()
        result = mapper.build_coverage(snapshot)

        self.assertGreaterEqual(result.usage_ratio_percent, 0.0)
        self.assertLessEqual(result.usage_ratio_percent, 100.0)
        self.assertIsInstance(result.used_methods, list)
        self.assertIsInstance(result.used_actions, list)
        self.assertIn("file_io", result.category_totals)
        self.assertIn("other", result.category_totals)


if __name__ == "__main__":
    unittest.main()


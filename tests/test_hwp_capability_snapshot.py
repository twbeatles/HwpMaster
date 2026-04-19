import unittest

from src.core.hwp_handler import HwpHandler
from src.core.capability_mapper import CapabilityMapper
from src.core.hwp_handler.types import CapabilitySnapshot


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

    def test_capability_mapper_preserves_snapshot_categories_without_methods(self) -> None:
        snapshot = CapabilitySnapshot(
            pyhwpx_version="unavailable",
            method_count=7,
            methods=[],
            action_count=0,
            actions=[],
            categories={
                "file_io": 2,
                "security_privacy": 1,
                "other": 4,
            },
            unsupported_categories=[],
        )

        mapper = CapabilityMapper()
        result = mapper.build_coverage(snapshot)

        self.assertEqual(result.total_public_methods, 7)
        self.assertEqual(result.used_public_methods, 0)
        self.assertEqual(result.category_totals["file_io"], 2)
        self.assertEqual(result.category_totals["other"], 4)


if __name__ == "__main__":
    unittest.main()

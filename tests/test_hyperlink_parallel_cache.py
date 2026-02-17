import threading
import time
import unittest

from src.core.hyperlink_checker import HyperlinkChecker, LinkCheckResult, LinkInfo, LinkStatus


class _FakeHyperlinkChecker(HyperlinkChecker):
    def __init__(
        self,
        urls: list[str],
        *,
        max_concurrency: int,
        cache_enabled: bool,
    ) -> None:
        super().__init__(
            external_requests_enabled=True,
            max_concurrency=max_concurrency,
            cache_enabled=cache_enabled,
        )
        self._urls = urls
        self.call_count = 0
        self._lock = threading.Lock()

    def extract_links(self, source_path: str) -> LinkCheckResult:
        links = [LinkInfo(url=u, text=u, page=0) for u in self._urls]
        return LinkCheckResult(success=True, source_path=source_path, links=links)

    def check_url(self, url: str) -> tuple[LinkStatus, str]:
        time.sleep(0.01)
        with self._lock:
            self.call_count += 1
        return LinkStatus.VALID, ""


class TestHyperlinkParallelCache(unittest.TestCase):
    def test_parallel_cache_preserves_order_and_dedupes(self) -> None:
        urls = [
            "https://a.example.com",
            "https://b.example.com",
            "https://a.example.com",
            "https://c.example.com",
            "https://b.example.com",
        ]
        checker = _FakeHyperlinkChecker(urls, max_concurrency=4, cache_enabled=True)

        result = checker.check_links("dummy.hwp")

        self.assertTrue(result.success)
        self.assertEqual([l.url for l in result.links], urls)
        self.assertEqual(result.valid_count, len(urls))
        self.assertEqual(checker.call_count, 3)

    def test_parallel_without_cache_checks_each_link(self) -> None:
        urls = [
            "https://a.example.com",
            "https://b.example.com",
            "https://a.example.com",
            "https://c.example.com",
            "https://b.example.com",
        ]
        checker = _FakeHyperlinkChecker(urls, max_concurrency=4, cache_enabled=False)

        result = checker.check_links("dummy.hwp")

        self.assertTrue(result.success)
        self.assertEqual(result.valid_count, len(urls))
        self.assertEqual(checker.call_count, len(urls))


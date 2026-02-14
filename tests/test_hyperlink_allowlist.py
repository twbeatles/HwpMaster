import unittest


from src.core.hyperlink_checker import parse_allowlist, host_in_allowlist


class TestHyperlinkAllowlist(unittest.TestCase):
    def test_parse_allowlist(self) -> None:
        self.assertEqual(parse_allowlist(""), [])
        self.assertEqual(parse_allowlist(" a.com,  *.b.com ,,c.com "), ["a.com", "*.b.com", "c.com"])

    def test_host_in_allowlist_exact(self) -> None:
        pats = ["example.com"]
        self.assertTrue(host_in_allowlist("example.com", pats))
        self.assertFalse(host_in_allowlist("a.example.com", pats))

    def test_host_in_allowlist_wildcard_subdomain(self) -> None:
        pats = ["*.example.com"]
        self.assertTrue(host_in_allowlist("example.com", pats))
        self.assertTrue(host_in_allowlist("a.example.com", pats))
        self.assertTrue(host_in_allowlist("a.b.example.com", pats))
        self.assertFalse(host_in_allowlist("evil.com", pats))

    def test_host_in_allowlist_fnmatch(self) -> None:
        pats = ["*.corp.local"]
        self.assertTrue(host_in_allowlist("x.corp.local", pats))
        self.assertFalse(host_in_allowlist("corp.local.evil", pats))


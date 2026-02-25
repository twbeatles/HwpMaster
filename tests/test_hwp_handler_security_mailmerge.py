import tempfile
import unittest
from pathlib import Path

from src.core.hwp_handler import ConversionResult, HwpHandler


class _FakeHwp:
    def __init__(self) -> None:
        self.opened: list[str] = []
        self.saved: list[tuple[str, dict]] = []
        self.fields: dict[str, str] = {}
        self.fail_fields = {"missing"}

    def open(self, path: str) -> None:
        self.opened.append(path)

    def save_as(self, output_path: str, **kwargs) -> None:
        # Simulate a pyhwpx build that does not support any password kwarg.
        if kwargs:
            raise TypeError("password kwargs not supported")
        self.saved.append((output_path, kwargs))

    def GetTextFile(self, _fmt: str, _opt: str) -> str:  # noqa: N802
        return "홍길동 900101-1234567, 연락처 010-1234-5678, email test@example.com"

    def set_document_info(self, _key: str, _value: str) -> None:
        return None

    def delete_all_comments(self) -> None:
        return None

    def accept_all_changes(self) -> None:
        return None

    def set_distribution_mode(self, _value: bool) -> None:
        return None

    def get_field_list(self) -> str:
        return "name;dept\ntitle\x02dept"

    def put_field_text(self, field_name: str, value: str) -> None:
        if field_name in self.fail_fields:
            raise RuntimeError("field not found")
        self.fields[field_name] = value


class _MailMergeTestHandler(HwpHandler):
    def __init__(self) -> None:
        super().__init__()
        self.saved_outputs: list[str] = []

    def _ensure_hwp(self) -> None:
        # mail-merge naming test does not need pyhwpx.
        return None

    def inject_data(self, template_path: str, data: dict[str, str], output_path: str) -> ConversionResult:
        self.saved_outputs.append(output_path)
        if data.get("fail") == "1":
            return ConversionResult(success=False, source_path=template_path, error_message="inject failed")
        return ConversionResult(success=True, source_path=template_path, output_path=output_path)


class TestHwpHandlerSecurityAndMailMerge(unittest.TestCase):
    def test_harden_document_collects_pii_and_password_warning(self) -> None:
        handler = HwpHandler()
        handler._hwp = _FakeHwp()  # type: ignore[attr-defined]

        result = handler.harden_document(
            "input.hwp",
            output_path="output.hwp",
            options={
                "scan_personal_info": True,
                "document_password": "1234",
                "strict_password": False,
            },
        )

        self.assertTrue(result.success)
        self.assertIn("pii_total", result.artifacts)
        self.assertGreater(int(result.artifacts.get("pii_total", 0)), 0)
        self.assertEqual(result.artifacts.get("password_requested"), True)
        self.assertEqual(result.artifacts.get("password_applied"), False)
        self.assertTrue(any("암호" in w for w in result.warnings))

    def test_harden_document_strict_password_fails_when_not_supported(self) -> None:
        handler = HwpHandler()
        handler._hwp = _FakeHwp()  # type: ignore[attr-defined]

        result = handler.harden_document(
            "input.hwp",
            output_path="output.hwp",
            options={
                "document_password": "1234",
                "strict_password": True,
            },
        )

        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)
        self.assertIn("암호", str(result.error))

    def test_list_fields_normalizes_and_deduplicates(self) -> None:
        handler = HwpHandler()
        handler._hwp = _FakeHwp()  # type: ignore[attr-defined]

        result = handler.list_fields("template.hwp")

        self.assertTrue(result.success)
        self.assertEqual(result.artifacts.get("fields"), ["name", "dept", "title"])

    def test_fill_fields_returns_missing_field_error_when_required(self) -> None:
        handler = HwpHandler()
        handler._hwp = _FakeHwp()  # type: ignore[attr-defined]

        result = handler.fill_fields(
            source_path="template.hwp",
            values={"name": "Alice", "missing": "X"},
            output_path="out.hwp",
            ignore_missing=False,
        )

        self.assertFalse(result.success)
        self.assertEqual(result.changed_count, 1)
        self.assertIn("missing", result.artifacts.get("missing_fields", []))

    def test_iter_inject_data_supports_filename_template(self) -> None:
        handler = _MailMergeTestHandler()
        rows = [
            {"name": "alice"},
            {"name": "bob"},
        ]

        with tempfile.TemporaryDirectory() as td:
            list(
                handler.iter_inject_data(
                    template_path="template.hwp",
                    data_iterable=rows,
                    output_dir=td,
                    filename_template="{name}_{index}",
                )
            )

            outputs = [Path(p).name for p in handler.saved_outputs]
            self.assertEqual(outputs, ["alice_0001.hwp", "bob_0002.hwp"])

    def test_mail_merge_reports_success_and_failure_counts(self) -> None:
        handler = _MailMergeTestHandler()
        rows = [
            {"name": "ok1"},
            {"name": "bad", "fail": "1"},
            {"name": "ok2"},
        ]

        with tempfile.TemporaryDirectory() as td:
            result = handler.mail_merge(
                template_path="template.hwp",
                data_iterable=rows,
                output_dir=td,
                filename_template="{name}_{index}",
                stop_on_error=False,
            )

        self.assertFalse(result.success)
        self.assertEqual(result.artifacts.get("success_count"), 2)
        self.assertEqual(result.artifacts.get("fail_count"), 1)
        self.assertEqual(len(result.artifacts.get("outputs", [])), 2)


if __name__ == "__main__":
    unittest.main()

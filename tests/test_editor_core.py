from __future__ import annotations

import json
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from src.core.editor import EditorAssetServer, EditorSaveService, EditorSession


class TestEditorCore(unittest.TestCase):
    def test_save_current_creates_single_backup_and_updates_session(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "doc.hwp"
            source.write_bytes(b"old")

            session = EditorSession.from_file(str(source))
            session.dirty = True
            service = EditorSaveService(root / "config")

            first = service.save(session, b"new", mode="current", output_format="hwp")
            self.assertTrue(first.success, first.error)
            self.assertEqual(source.read_bytes(), b"new")
            self.assertTrue(first.backup_path)
            self.assertEqual(Path(first.backup_path).read_bytes(), b"old")
            self.assertFalse(session.dirty)
            self.assertEqual(session.document_bytes, b"new")

            second = service.save(session, b"newer", mode="current", output_format="hwp")
            self.assertTrue(second.success, second.error)
            backups = list((root / "config" / "editor_backups").glob("*.bak.hwp"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(source.read_bytes(), b"newer")

    def test_hwpx_current_overwrite_is_blocked_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "doc.hwpx"
            source.write_bytes(b"hwpx")

            session = EditorSession.from_file(str(source))
            result = EditorSaveService(root / "config").save(
                session,
                b"changed",
                mode="current",
                output_format="hwpx",
            )

            self.assertFalse(result.success)
            self.assertIn("HWPX", result.error or "")
            self.assertEqual(source.read_bytes(), b"hwpx")

    def test_save_recovery_writes_recovery_without_clearing_dirty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "doc.hwp"
            source.write_bytes(b"old")

            session = EditorSession.from_file(str(source))
            session.dirty = True
            result = EditorSaveService(root / "config").save(
                session,
                b"snapshot",
                mode="recovery",
                output_format="hwp",
            )

            self.assertTrue(result.success, result.error)
            self.assertTrue(result.recovery)
            self.assertEqual(Path(result.path).read_bytes(), b"snapshot")
            self.assertTrue(session.dirty)
            self.assertEqual(source.read_bytes(), b"old")

    def test_asset_server_document_requires_session_token(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            asset_dir = root / "assets"
            asset_dir.mkdir()
            (asset_dir / "index.html").write_text("ok", encoding="utf-8")

            source = root / "doc.hwp"
            source.write_bytes(b"document")
            session = EditorSession.from_file(str(source))
            server = EditorAssetServer(
                asset_dir=asset_dir,
                save_service=EditorSaveService(root / "config"),
            )
            try:
                server.start()
                server.register_session(session)
                base = server.base_url

                ok_url = f"{base}/api/sessions/{session.session_id}/document?token={session.token}"
                with urllib.request.urlopen(ok_url, timeout=5) as response:
                    self.assertEqual(response.read(), b"document")

                bad_url = f"{base}/api/sessions/{session.session_id}/document?token=bad"
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(bad_url, timeout=5)
                self.assertEqual(ctx.exception.code, 403)
            finally:
                server.stop()

    def test_asset_server_rejects_static_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            asset_dir = root / "assets"
            asset_dir.mkdir()
            (asset_dir / "index.html").write_text("ok", encoding="utf-8")
            (root / "secret.txt").write_text("secret", encoding="utf-8")

            server = EditorAssetServer(
                asset_dir=asset_dir,
                save_service=EditorSaveService(root / "config"),
            )
            try:
                server.start()
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(f"{server.base_url}/../secret.txt", timeout=5)
                self.assertEqual(ctx.exception.code, 404)
            finally:
                server.stop()

    def test_asset_server_save_endpoint_updates_state(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            asset_dir = root / "assets"
            asset_dir.mkdir()
            (asset_dir / "index.html").write_text("ok", encoding="utf-8")

            source = root / "doc.hwp"
            source.write_bytes(b"old")
            session = EditorSession.from_file(str(source))
            server = EditorAssetServer(
                asset_dir=asset_dir,
                save_service=EditorSaveService(root / "config"),
            )
            try:
                server.start()
                server.register_session(session)
                url = (
                    f"{server.base_url}/api/sessions/{session.session_id}/save"
                    f"?token={session.token}&mode=current&format=hwp"
                )
                request = urllib.request.Request(url, data=b"new", method="POST")
                with urllib.request.urlopen(request, timeout=5) as response:
                    payload = json.loads(response.read().decode("utf-8"))

                self.assertTrue(payload["success"])
                self.assertEqual(source.read_bytes(), b"new")
                self.assertEqual(session.document_bytes, b"new")
            finally:
                server.stop()

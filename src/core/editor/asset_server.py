from __future__ import annotations

import json
import mimetypes
import sys
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, quote, unquote, urlparse

from .save_service import EditorSaveService
from .session import EditorSession


def default_asset_dir() -> Path:
    bundle_dir = getattr(sys, "_MEIPASS", None) if getattr(sys, "frozen", False) else None
    base_path = Path(bundle_dir) if bundle_dir else Path(__file__).resolve().parents[3]
    return base_path / "assets" / "rhwp_studio"


class EditorAssetServer:
    """Localhost-only static/API server for the embedded rhwp editor."""

    def __init__(
        self,
        *,
        asset_dir: str | Path | None = None,
        save_service: EditorSaveService,
        host: str = "127.0.0.1",
    ) -> None:
        self.asset_dir = Path(asset_dir) if asset_dir is not None else default_asset_dir()
        self.save_service = save_service
        self.host = host
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._sessions: dict[str, EditorSession] = {}

    @property
    def is_running(self) -> bool:
        return self._server is not None

    @property
    def base_url(self) -> str:
        if self._server is None:
            raise RuntimeError("EditorAssetServer is not running")
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    def start(self) -> None:
        if self._server is not None:
            return
        handler_cls = self._build_handler()
        self._server = ThreadingHTTPServer((self.host, 0), handler_cls)
        self._thread = threading.Thread(target=self._server.serve_forever, name="hwp-master-editor-server", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        server = self._server
        if server is None:
            return
        server.shutdown()
        server.server_close()
        self._server = None
        self._thread = None

    def register_session(self, session: EditorSession) -> None:
        self._sessions[session.session_id] = session

    def unregister_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def get_session(self, session_id: str) -> Optional[EditorSession]:
        return self._sessions.get(session_id)

    def editor_url(self, session: EditorSession) -> str:
        self.start()
        api_base = quote(self.base_url, safe="")
        return (
            f"{self.base_url}/index.html"
            f"?session={quote(session.session_id)}"
            f"&token={quote(session.token)}"
            f"&apiBase={api_base}"
        )

    def _build_handler(self):
        owner = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "HwpMasterEditor/1.0"

            def log_message(self, format: str, *args) -> None:  # noqa: A002
                return

            def do_GET(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path.startswith("/api/"):
                    self._handle_api_get(parsed)
                    return
                self._serve_static(parsed.path)

            def do_POST(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path.startswith("/api/"):
                    self._handle_api_post(parsed)
                    return
                self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

            def _session_from_path(self, path: str, query: dict[str, list[str]]) -> Optional[EditorSession]:
                parts = [part for part in path.split("/") if part]
                if len(parts) < 3 or parts[0] != "api" or parts[1] != "sessions":
                    self._send_json({"error": "invalid api path"}, status=HTTPStatus.NOT_FOUND)
                    return None
                session = owner.get_session(parts[2])
                if session is None:
                    self._send_json({"error": "session not found"}, status=HTTPStatus.NOT_FOUND)
                    return None
                token = query.get("token", [""])[0]
                if not session.verify_token(token):
                    self._send_json({"error": "invalid token"}, status=HTTPStatus.FORBIDDEN)
                    return None
                return session

            def _handle_api_get(self, parsed) -> None:
                query = parse_qs(parsed.query)
                session = self._session_from_path(parsed.path, query)
                if session is None:
                    return
                if parsed.path.endswith("/document"):
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", self._document_content_type(session))
                    self.send_header("Content-Length", str(len(session.document_bytes)))
                    self.send_header("X-HwpMaster-File-Name", quote(session.file_name))
                    self.end_headers()
                    self.wfile.write(session.document_bytes)
                    return
                if parsed.path.endswith("/state"):
                    self._send_json(session.to_dict())
                    return
                self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

            def _handle_api_post(self, parsed) -> None:
                query = parse_qs(parsed.query)
                session = self._session_from_path(parsed.path, query)
                if session is None:
                    return
                length = int(self.headers.get("Content-Length", "0") or "0")
                body = self.rfile.read(length) if length > 0 else b""

                if parsed.path.endswith("/state"):
                    try:
                        payload = json.loads(body.decode("utf-8") if body else "{}")
                        if not isinstance(payload, dict):
                            raise ValueError("state payload must be an object")
                        session.update_state(payload)
                        self._send_json(session.to_dict())
                    except Exception as e:
                        self._send_json({"error": str(e)}, status=HTTPStatus.BAD_REQUEST)
                    return

                if parsed.path.endswith("/save"):
                    mode = query.get("mode", ["current"])[0]
                    output_format = query.get("format", [session.source_format])[0]
                    target_path = unquote(query.get("target", [""])[0])
                    result = owner.save_service.save(
                        session,
                        body,
                        mode=mode,
                        output_format=output_format,
                        target_path=target_path,
                    )
                    status = HTTPStatus.OK if result.success else HTTPStatus.BAD_REQUEST
                    self._send_json(result.to_dict(), status=status)
                    return

                self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

            def _serve_static(self, path: str) -> None:
                requested = "index.html" if path in {"", "/"} else unquote(path.lstrip("/"))
                root = owner.asset_dir.resolve()
                target = (root / requested).resolve()
                try:
                    target.relative_to(root)
                except ValueError:
                    self._send_json({"error": "asset not found"}, status=HTTPStatus.NOT_FOUND)
                    return
                if not target.is_file():
                    self._send_json({"error": "asset not found"}, status=HTTPStatus.NOT_FOUND)
                    return
                content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
                if target.suffix == ".js":
                    content_type = "text/javascript; charset=utf-8"
                elif target.suffix == ".wasm":
                    content_type = "application/wasm"
                elif target.suffix in {".html", ".css"}:
                    content_type = f"text/{target.suffix.lstrip('.')}; charset=utf-8"
                data = target.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)

            def _document_content_type(self, session: EditorSession) -> str:
                if session.source_format == "hwpx":
                    return "application/zip"
                return "application/x-hwp"

            def _send_json(self, payload: dict[str, object], *, status: HTTPStatus = HTTPStatus.OK) -> None:
                data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)

        return Handler

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.editor import EditorAssetServer, EditorSaveService, EditorSession
from ...utils.history_manager import TaskType
from ...utils.settings import get_settings_manager
from ...utils.task_tracking import record_task_summary, track_recent_files
from ..widgets.page_header import PageHeader
from ..widgets.toast import get_toast_manager


class _EditorBridge(QObject):
    """QtWebChannel bridge used by the embedded rhwp page."""

    def __init__(self, page: "EditorPage") -> None:
        super().__init__(page)
        self._page = page

    @Slot(str, result=str)
    def requestSaveAs(self, suggested_name: str = "") -> str:  # noqa: N802
        return self._page.select_save_as_path(suggested_name)


class EditorPage(QWidget):
    """Embedded rhwp-based HWP/HWPX editor workspace."""

    send_to_convert_requested = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._settings = get_settings_manager()
        self._save_service = EditorSaveService(self._settings.config_dir)
        self._server = EditorAssetServer(save_service=self._save_service)
        self._session: Optional[EditorSession] = None
        self._web_view = None
        self._web_channel = None
        self._bridge: Optional[_EditorBridge] = None
        self._last_recorded_saved_path = ""

        self._setup_ui()
        self._status_timer = QTimer(self)
        self._status_timer.setInterval(1000)
        self._status_timer.timeout.connect(self._refresh_session_status)
        self._status_timer.start()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        header = PageHeader(
            "문서 편집",
            "rhwp WebAssembly 엔진으로 HWP/HWPX 문서를 열고 편집합니다.",
            "✍",
        )
        layout.addWidget(header)

        command_bar = QFrame()
        command_bar.setObjectName("editorCommandBar")
        command_layout = QHBoxLayout(command_bar)
        command_layout.setContentsMargins(14, 12, 14, 12)
        command_layout.setSpacing(10)

        self.open_btn = QPushButton("문서 열기")
        self.open_btn.clicked.connect(self.open_document)
        command_layout.addWidget(self.open_btn)

        self.save_btn = QPushButton("저장")
        self.save_btn.setProperty("class", "secondary")
        self.save_btn.clicked.connect(self.save_current)
        command_layout.addWidget(self.save_btn)

        self.save_as_btn = QPushButton("다른 이름 저장")
        self.save_as_btn.setProperty("class", "secondary")
        self.save_as_btn.clicked.connect(self.save_as)
        command_layout.addWidget(self.save_as_btn)

        self.recovery_btn = QPushButton("복구본 저장")
        self.recovery_btn.setProperty("class", "secondary")
        self.recovery_btn.clicked.connect(self.save_recovery)
        command_layout.addWidget(self.recovery_btn)

        self.send_to_convert_btn = QPushButton("변환 목록으로 보내기")
        self.send_to_convert_btn.setProperty("class", "secondary")
        self.send_to_convert_btn.clicked.connect(self.send_current_to_convert)
        command_layout.addWidget(self.send_to_convert_btn)

        command_layout.addStretch()
        self.status_label = QLabel("문서를 열어주세요.")
        self.status_label.setStyleSheet("color: #8b949e;")
        command_layout.addWidget(self.status_label)
        layout.addWidget(command_bar)

        self.web_container = QFrame()
        self.web_container.setObjectName("editorWebContainer")
        web_layout = QVBoxLayout(self.web_container)
        web_layout.setContentsMargins(0, 0, 0, 0)
        web_layout.setSpacing(0)
        layout.addWidget(self.web_container, 1)

        self._init_web_view(web_layout)
        self._update_button_state()

    def _init_web_view(self, layout: QVBoxLayout) -> None:
        try:
            from PySide6.QtWebChannel import QWebChannel
            from PySide6.QtWebEngineWidgets import QWebEngineView

            self._web_view = QWebEngineView()
            self._web_channel = QWebChannel(self._web_view.page())
            self._bridge = _EditorBridge(self)
            self._web_channel.registerObject("hwpMaster", self._bridge)
            self._web_view.page().setWebChannel(self._web_channel)
            layout.addWidget(self._web_view)
        except Exception as e:
            self._web_view = None
            message = QLabel(f"QtWebEngine 초기화 실패: {e}")
            message.setWordWrap(True)
            message.setStyleSheet("color: #f85149; padding: 24px;")
            layout.addWidget(message)

    @property
    def current_session(self) -> Optional[EditorSession]:
        return self._session

    @Slot()
    def open_document(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "편집할 문서 선택",
            self._settings.get("default_output_dir", ""),
            "HWP 파일 (*.hwp *.hwpx)",
        )
        if file_path:
            self.load_document(file_path)

    def load_document(self, file_path: str) -> None:
        if self._web_view is None:
            QMessageBox.warning(self, "오류", "QtWebEngine을 사용할 수 없어 편집기를 열 수 없습니다.")
            return

        try:
            session = EditorSession.from_file(file_path)
            self._server.start()
            self._server.register_session(session)
            if self._session is not None:
                self._server.unregister_session(self._session.session_id)
            self._session = session
            self._last_recorded_saved_path = ""
            track_recent_files([file_path], settings=self._settings)

            from PySide6.QtCore import QUrl

            self._web_view.setUrl(QUrl(self._server.editor_url(session)))
            self.status_label.setText(f"열림: {Path(file_path).name}")
            self._update_button_state()
        except Exception as e:
            QMessageBox.warning(self, "문서 열기 실패", str(e))

    @Slot()
    def save_current(self) -> None:
        self._run_editor_script("window.HwpMasterEditor && window.HwpMasterEditor.requestSave('current')")

    @Slot()
    def save_as(self) -> None:
        suggested = self._suggested_save_name()
        target = self.select_save_as_path(suggested)
        if target:
            escaped = target.replace("\\", "\\\\").replace("'", "\\'")
            self._run_editor_script(f"window.HwpMasterEditor && window.HwpMasterEditor.requestSaveAs('{escaped}')")

    @Slot()
    def save_recovery(self) -> None:
        self._run_editor_script("window.HwpMasterEditor && window.HwpMasterEditor.requestSave('recovery')")

    @Slot()
    def send_current_to_convert(self) -> None:
        if self._session is None:
            return
        if self._session.dirty:
            QMessageBox.information(self, "저장 필요", "수정 중인 문서를 저장한 뒤 변환 목록으로 보냅니다.")
            self.save_current()
            return
        path = self._session.current_path or self._session.source_path
        if path:
            self.send_to_convert_requested.emit(path)

    def select_save_as_path(self, suggested_name: str = "") -> str:
        default_dir = self._settings.get("default_output_dir", "") or str(Path.home() / "Documents")
        default_name = suggested_name or self._suggested_save_name()
        default_path = str(Path(default_dir) / Path(default_name).name)
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "다른 이름 저장",
            default_path,
            "HWP 파일 (*.hwp);;HWPX 파일 (*.hwpx)",
        )
        return file_path or ""

    def _suggested_save_name(self) -> str:
        if self._session is None:
            return "document.hwp"
        current = Path(self._session.current_path or self._session.source_path)
        suffix = current.suffix if current.suffix.lower() in {".hwp", ".hwpx"} else ".hwp"
        return f"{current.stem}_edited{suffix}"

    def _run_editor_script(self, script: str) -> None:
        if self._web_view is None or self._session is None:
            QMessageBox.information(self, "알림", "먼저 문서를 열어주세요.")
            return
        self._web_view.page().runJavaScript(script)

    def _refresh_session_status(self) -> None:
        session = self._session
        if session is None:
            self.status_label.setText("문서를 열어주세요.")
            self._update_button_state()
            return

        dirty = "수정됨" if session.dirty else "저장됨"
        page_info = f"{session.page_count}쪽" if session.page_count else "쪽 수 확인 중"
        status = session.status_message or "대기 중"
        self.status_label.setText(f"{session.display_name} · {dirty} · {page_info} · {status}")
        self._record_saved_session_once(session)
        self._update_button_state()

    def _record_saved_session_once(self, session: EditorSession) -> None:
        saved_path = str(session.last_saved_path or "").strip()
        if not saved_path or saved_path == self._last_recorded_saved_path:
            return
        self._last_recorded_saved_path = saved_path
        track_recent_files([saved_path], settings=self._settings)
        record_task_summary(
            TaskType.EDITOR,
            "문서 편집 저장",
            [session.source_path],
            1,
            0,
            options={
                "saved_path": saved_path,
                "backup_path": session.backup_path,
            },
            settings=self._settings,
            recent_files=[saved_path],
        )
        get_toast_manager().success("문서 저장 완료")

    def _update_button_state(self) -> None:
        has_doc = self._session is not None and self._web_view is not None
        self.save_btn.setEnabled(has_doc)
        self.save_as_btn.setEnabled(has_doc)
        self.recovery_btn.setEnabled(has_doc)
        self.send_to_convert_btn.setEnabled(has_doc)

    def closeEvent(self, event) -> None:  # noqa: N802
        try:
            self._server.stop()
        except Exception:
            pass
        super().closeEvent(event)

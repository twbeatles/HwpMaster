"""
Advanced action console page.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QFileDialog,
    QPlainTextEdit,
    QTextEdit,
    QCheckBox,
    QMessageBox,
    QGroupBox,
    QComboBox,
    QLineEdit,
)

from ...core.action_runner import ActionRunner, ActionCommand
from ..widgets.page_header import PageHeader
from ..widgets.progress_card import ProgressCard
from ..widgets.toast import get_toast_manager


class ActionConsolePage(QWidget):
    """pyhwpx 고급 액션 콘솔."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._runner = ActionRunner()
        self._worker = None
        self._setup_ui()
        self._reload_templates()
        self._reload_builtin_presets()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        page_header = PageHeader(
            "고급 액션 콘솔",
            "pyhwpx Run/Execute 액션을 JSON으로 실행하고 재사용합니다.",
            "🧰",
        )
        layout.addWidget(page_header)

        source_group = QGroupBox("대상 문서 (선택)")
        source_layout = QHBoxLayout(source_group)
        self.source_path_edit = QLineEdit()
        self.source_path_edit.setPlaceholderText("열어둘 HWP/HWPX 파일 경로 (선택)")
        source_layout.addWidget(self.source_path_edit, 1)
        browse_btn = QPushButton("파일 선택...")
        browse_btn.clicked.connect(self._on_select_source)
        source_layout.addWidget(browse_btn)
        layout.addWidget(source_group)

        builtin_group = QGroupBox("Built-in Phase 3 Presets")
        builtin_layout = QHBoxLayout(builtin_group)
        self.builtin_preset_combo = QComboBox()
        builtin_layout.addWidget(self.builtin_preset_combo, 1)
        load_builtin_btn = QPushButton("Load to JSON")
        load_builtin_btn.clicked.connect(self._on_load_builtin_preset)
        builtin_layout.addWidget(load_builtin_btn)
        run_builtin_btn = QPushButton("Run Preset")
        run_builtin_btn.clicked.connect(self._on_run_builtin_preset)
        builtin_layout.addWidget(run_builtin_btn)
        layout.addWidget(builtin_group)

        editor_group = QGroupBox("액션 명령 JSON")
        editor_layout = QVBoxLayout(editor_group)
        self.command_editor = QPlainTextEdit()
        self.command_editor.setPlaceholderText(
            '[\n'
            '  {"action_type":"run","action_id":"MoveDocBegin","description":"문서 시작 이동"},\n'
            '  {"action_type":"execute","action_id":"InsertText","pset_name":"HInsertText","values":{"Text":"테스트\\r\\n"}}\n'
            ']'
        )
        editor_layout.addWidget(self.command_editor)
        layout.addWidget(editor_group, 1)

        options_row = QHBoxLayout()
        self.stop_on_error_check = QCheckBox("오류 발생 시 즉시 중단")
        self.stop_on_error_check.setChecked(True)
        options_row.addWidget(self.stop_on_error_check)
        options_row.addStretch()
        layout.addLayout(options_row)

        template_group = QGroupBox("사용자 템플릿")
        template_layout = QVBoxLayout(template_group)

        top_row = QHBoxLayout()
        self.template_name_edit = QLineEdit()
        self.template_name_edit.setPlaceholderText("템플릿 이름")
        top_row.addWidget(self.template_name_edit, 1)
        save_template_btn = QPushButton("템플릿 저장")
        save_template_btn.clicked.connect(self._on_save_template)
        top_row.addWidget(save_template_btn)
        template_layout.addLayout(top_row)

        bottom_row = QHBoxLayout()
        self.template_combo = QComboBox()
        bottom_row.addWidget(self.template_combo, 1)
        load_template_btn = QPushButton("불러오기")
        load_template_btn.clicked.connect(self._on_load_template)
        bottom_row.addWidget(load_template_btn)
        delete_template_btn = QPushButton("삭제")
        delete_template_btn.clicked.connect(self._on_delete_template)
        bottom_row.addWidget(delete_template_btn)
        run_template_btn = QPushButton("선택 템플릿 실행")
        run_template_btn.clicked.connect(self._on_run_template)
        bottom_row.addWidget(run_template_btn)
        template_layout.addLayout(bottom_row)

        layout.addWidget(template_group)

        self.progress_card = ProgressCard()
        self.progress_card.setVisible(False)
        layout.addWidget(self.progress_card)

        run_row = QHBoxLayout()
        run_row.addStretch()
        self.run_btn = QPushButton("JSON 액션 실행")
        self.run_btn.clicked.connect(self._on_run_commands)
        run_row.addWidget(self.run_btn)
        layout.addLayout(run_row)

        result_group = QGroupBox("실행 로그")
        result_layout = QVBoxLayout(result_group)
        self.result_log = QTextEdit()
        self.result_log.setReadOnly(True)
        result_layout.addWidget(self.result_log)
        layout.addWidget(result_group, 1)

    def _reload_templates(self) -> None:
        current = self.template_combo.currentText()
        self.template_combo.blockSignals(True)
        self.template_combo.clear()
        for tpl in sorted(self._runner.list_templates(), key=lambda t: t.name.lower()):
            self.template_combo.addItem(tpl.name)
        if current:
            idx = self.template_combo.findText(current)
            if idx >= 0:
                self.template_combo.setCurrentIndex(idx)
        self.template_combo.blockSignals(False)

    def _reload_builtin_presets(self) -> None:
        current_id = self._current_builtin_preset_id()
        self.builtin_preset_combo.blockSignals(True)
        self.builtin_preset_combo.clear()
        for preset in self._runner.list_builtin_presets():
            self.builtin_preset_combo.addItem(f"[{preset.category}] {preset.name}", preset.preset_id)
        if current_id:
            for idx in range(self.builtin_preset_combo.count()):
                if str(self.builtin_preset_combo.itemData(idx)) == current_id:
                    self.builtin_preset_combo.setCurrentIndex(idx)
                    break
        self.builtin_preset_combo.blockSignals(False)

    def _current_builtin_preset_id(self) -> str:
        idx = self.builtin_preset_combo.currentIndex()
        if idx < 0:
            return ""
        return str(self.builtin_preset_combo.itemData(idx) or "").strip()

    @Slot()
    def _on_select_source(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "대상 문서 선택",
            "",
            "HWP 파일 (*.hwp *.hwpx)",
        )
        if path:
            self.source_path_edit.setText(path)

    def _parse_editor_commands(self) -> list[dict[str, Any]]:
        raw = self.command_editor.toPlainText().strip()
        if not raw:
            raise ValueError("액션 JSON이 비어 있습니다.")
        payload = json.loads(raw)
        if isinstance(payload, dict):
            payload = [payload]
        if not isinstance(payload, list):
            raise ValueError("액션 JSON은 객체 또는 객체 배열이어야 합니다.")
        commands: list[dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                raise ValueError("액션 항목은 객체여야 합니다.")
            action_type = str(item.get("action_type", "run")).strip().lower()
            action_id = str(item.get("action_id", "")).strip()
            if not action_id:
                raise ValueError("action_id는 필수입니다.")
            if action_type not in ("run", "execute"):
                raise ValueError(f"지원하지 않는 action_type: {action_type}")
            commands.append(
                {
                    "action_type": action_type,
                    "action_id": action_id,
                    "pset_name": str(item.get("pset_name", "")),
                    "values": dict(item.get("values", {}) or {}),
                    "description": str(item.get("description", "")),
                }
            )
        return commands

    def _set_running(self, running: bool) -> None:
        self.run_btn.setEnabled(not running)
        self.progress_card.setVisible(True)
        if running:
            self.progress_card.reset()
            self.progress_card.set_status("액션 실행 중...")

    @Slot()
    def _on_run_commands(self) -> None:
        try:
            commands = self._parse_editor_commands()
        except Exception as e:
            QMessageBox.warning(self, "JSON 오류", str(e))
            return
        self._start_worker(commands)

    @Slot()
    def _on_run_template(self) -> None:
        name = self.template_combo.currentText().strip()
        if not name:
            QMessageBox.warning(self, "오류", "실행할 템플릿을 선택해주세요.")
            return
        tpl = self._runner.get_template(name)
        if tpl is None:
            QMessageBox.warning(self, "오류", "템플릿을 찾을 수 없습니다.")
            self._reload_templates()
            return
        commands = [asdict_cmd for asdict_cmd in [cmd.__dict__ for cmd in tpl.commands]]
        self._start_worker(commands)

    @Slot()
    def _on_load_builtin_preset(self) -> None:
        preset_id = self._current_builtin_preset_id()
        if not preset_id:
            QMessageBox.warning(self, "오류", "프리셋을 선택해주세요.")
            return

        preset = self._runner.get_builtin_preset(preset_id)
        if preset is None:
            QMessageBox.warning(self, "오류", f"프리셋을 찾을 수 없습니다: {preset_id}")
            return

        commands = self._runner.build_builtin_preset_commands(preset_id)
        payload = [cmd.__dict__ for cmd in commands]
        self.command_editor.setPlainText(json.dumps(payload, ensure_ascii=False, indent=2))
        self.template_name_edit.setText(preset.name)
        self.result_log.setPlainText(f"Loaded preset: {preset.preset_id}\n{preset.description}")

    @Slot()
    def _on_run_builtin_preset(self) -> None:
        preset_id = self._current_builtin_preset_id()
        if not preset_id:
            QMessageBox.warning(self, "오류", "프리셋을 선택해주세요.")
            return
        commands = [cmd.__dict__ for cmd in self._runner.build_builtin_preset_commands(preset_id)]
        if not commands:
            QMessageBox.warning(self, "오류", f"프리셋을 찾을 수 없습니다: {preset_id}")
            return
        self._start_worker(commands)

    def _start_worker(self, commands: list[dict[str, Any]]) -> None:
        from ...utils.worker import ActionConsoleWorker

        self._set_running(True)
        if self._worker is not None:
            try:
                self.progress_card.cancelled.disconnect(self._worker.cancel)
            except Exception:
                pass

        self._worker = ActionConsoleWorker(
            self.source_path_edit.text().strip(),
            commands,
            stop_on_error=self.stop_on_error_check.isChecked(),
        )
        self.progress_card.cancelled.connect(self._worker.cancel)
        self._worker.progress.connect(
            lambda c, t, n: (
                self.progress_card.set_count(c, t),
                self.progress_card.set_current_file(n),
            )
        )
        self._worker.status_changed.connect(self.progress_card.set_status)
        self._worker.error_occurred.connect(self._on_run_error)
        self._worker.finished_with_result.connect(self._on_run_finished)
        self._worker.start()

    @Slot(object)
    def _on_run_finished(self, result: Any) -> None:
        self._set_running(False)
        data = result.data or {}
        if data.get("cancelled"):
            self.progress_card.set_error("작업이 취소되었습니다.")
            return

        success_count = int(data.get("success_count", 0))
        fail_count = int(data.get("fail_count", 0))
        changed_count = int(data.get("changed_count", 0))
        warnings = data.get("warnings", [])
        artifacts = data.get("artifacts", {})

        if result.success:
            self.progress_card.set_completed(success_count, fail_count)
            get_toast_manager().success("액션 실행 완료")
        else:
            self.progress_card.set_error(result.error_message or "실행 실패")
            get_toast_manager().error(result.error_message or "실행 실패")

        lines = [
            f"success={bool(result.success)}",
            f"success_count={success_count}",
            f"fail_count={fail_count}",
            f"changed_count={changed_count}",
        ]
        if warnings:
            lines.append("warnings:")
            lines.extend(f"- {w}" for w in warnings)
        failed = artifacts.get("failed_commands", [])
        if failed:
            lines.append("failed_commands:")
            for item in failed:
                lines.append(json.dumps(item, ensure_ascii=False))
        self.result_log.setPlainText("\n".join(lines))

    @Slot(str)
    def _on_run_error(self, message: str) -> None:
        self.result_log.setPlainText(message)

    @Slot()
    def _on_save_template(self) -> None:
        name = self.template_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "오류", "템플릿 이름을 입력해주세요.")
            return
        try:
            raw_commands = self._parse_editor_commands()
            commands = [
                ActionCommand(
                    action_type=str(raw.get("action_type", "run")),
                    action_id=str(raw.get("action_id", "")),
                    pset_name=str(raw.get("pset_name", "")),
                    values=dict(raw.get("values", {}) or {}),
                    description=str(raw.get("description", "")),
                )
                for raw in raw_commands
            ]
        except Exception as e:
            QMessageBox.warning(self, "JSON 오류", str(e))
            return

        if not self._runner.save_template(name, commands):
            QMessageBox.warning(self, "오류", "템플릿 저장에 실패했습니다.")
            return
        self._reload_templates()
        idx = self.template_combo.findText(name)
        if idx >= 0:
            self.template_combo.setCurrentIndex(idx)
        get_toast_manager().success(f"템플릿 저장: {name}")

    @Slot()
    def _on_load_template(self) -> None:
        name = self.template_combo.currentText().strip()
        if not name:
            return
        tpl = self._runner.get_template(name)
        if tpl is None:
            QMessageBox.warning(self, "오류", "템플릿을 찾을 수 없습니다.")
            self._reload_templates()
            return
        payload = [cmd.__dict__ for cmd in tpl.commands]
        self.command_editor.setPlainText(json.dumps(payload, ensure_ascii=False, indent=2))
        self.template_name_edit.setText(name)

    @Slot()
    def _on_delete_template(self) -> None:
        name = self.template_combo.currentText().strip()
        if not name:
            return
        if QMessageBox.question(
            self,
            "템플릿 삭제",
            f"'{name}' 템플릿을 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        if self._runner.delete_template(name):
            self._reload_templates()
            get_toast_manager().success(f"템플릿 삭제: {name}")
        else:
            QMessageBox.warning(self, "오류", "템플릿 삭제에 실패했습니다.")

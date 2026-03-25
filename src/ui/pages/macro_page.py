"""
Macro Page
HWP 매크로 레코더 UI

Author: HWP Master
"""

from pathlib import Path
from typing import Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem,
    QFrame, QLineEdit, QTextEdit, QFileDialog,
    QMessageBox, QDialog, QFormLayout, QCheckBox,
    QSpinBox, QComboBox, QSplitter, QInputDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from ...core.macro_recorder import MacroRecorder, MacroInfo, MacroAction
from ...utils.history_manager import TaskType
from ..widgets.progress_card import ProgressCard
from ..widgets.page_header import PageHeader
from ...utils.worker import MacroRunWorker, WorkerResult
from ...utils.settings import get_settings_manager
from ...utils.task_tracking import record_task_result, track_recent_files


class MacroListItem(QListWidgetItem):
    """매크로 리스트 아이템"""
    
    def __init__(self, macro: MacroInfo) -> None:
        super().__init__()
        self.macro = macro
        self.setText(f"🎬 {macro.name}")
        self.setToolTip(f"{macro.description}\n액션 수: {len(macro.actions)}\n실행 횟수: {macro.run_count}")


class CreateMacroDialog(QDialog):
    """매크로 생성 다이얼로그"""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("새 매크로 만들기")
        self.setFixedSize(500, 400)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # 매크로 타입 선택
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("매크로 타입:"))
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["찾기/바꾸기", "서식 변경", "빈 매크로"])
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_layout.addWidget(self.type_combo)
        type_layout.addStretch()
        
        layout.addLayout(type_layout)
        
        # 기본 정보
        form = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("매크로 이름")
        form.addRow("이름:", self.name_edit)
        
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("매크로 설명 (선택사항)")
        form.addRow("설명:", self.desc_edit)
        
        layout.addLayout(form)
        
        # 찾기/바꾸기 옵션
        self.find_replace_frame = QFrame()
        fr_layout = QFormLayout(self.find_replace_frame)
        
        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("찾을 텍스트")
        fr_layout.addRow("찾기:", self.find_edit)
        
        self.replace_edit = QLineEdit()
        self.replace_edit.setPlaceholderText("바꿀 텍스트")
        fr_layout.addRow("바꾸기:", self.replace_edit)
        
        layout.addWidget(self.find_replace_frame)
        
        # 서식 옵션
        self.format_frame = QFrame()
        fmt_layout = QFormLayout(self.format_frame)
        
        self.bold_check = QCheckBox("굵게")
        self.italic_check = QCheckBox("기울임")
        self.underline_check = QCheckBox("밑줄")
        
        style_layout = QHBoxLayout()
        style_layout.addWidget(self.bold_check)
        style_layout.addWidget(self.italic_check)
        style_layout.addWidget(self.underline_check)
        style_layout.addStretch()
        fmt_layout.addRow("스타일:", style_layout)
        
        self.color_combo = QComboBox()
        self.color_combo.addItems(["선택 안함", "빨강", "파랑", "초록", "노랑", "검정"])
        fmt_layout.addRow("색상:", self.color_combo)
        
        self.size_spin = QSpinBox()
        self.size_spin.setRange(0, 100)
        self.size_spin.setValue(0)
        self.size_spin.setSpecialValueText("변경 안함")
        fmt_layout.addRow("크기:", self.size_spin)
        
        layout.addWidget(self.format_frame)
        self.format_frame.hide()
        
        layout.addStretch()
        
        # 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("취소")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        create_btn = QPushButton("생성")
        create_btn.clicked.connect(self.accept)
        btn_layout.addWidget(create_btn)
        
        layout.addLayout(btn_layout)
    
    def _on_type_changed(self, index: int) -> None:
        self.find_replace_frame.setVisible(index == 0)
        self.format_frame.setVisible(index == 1)
    
    def get_data(self) -> dict[str, Any]:
        color_map = {
            "빨강": "#FF0000",
            "파랑": "#0000FF",
            "초록": "#00FF00",
            "노랑": "#FFFF00",
            "검정": "#000000",
        }
        
        return {
            "type": self.type_combo.currentIndex(),
            "name": self.name_edit.text(),
            "description": self.desc_edit.text(),
            "find": self.find_edit.text(),
            "replace": self.replace_edit.text(),
            "bold": self.bold_check.isChecked(),
            "italic": self.italic_check.isChecked(),
            "underline": self.underline_check.isChecked(),
            "color": color_map.get(self.color_combo.currentText()),
            "size": self.size_spin.value() if self.size_spin.value() > 0 else None,
        }


class MacroPage(QWidget):
    """매크로 레코더 페이지"""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        
        self._recorder = MacroRecorder()
        self._worker: Optional[MacroRunWorker] = None
        self._settings = get_settings_manager()
        
        self._setup_ui()
        self._load_macros()
        self._sync_recording_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # 페이지 헤더
        header = PageHeader(
            "HWP 매크로 레코더",
            "반복적인 HWP 작업을 매크로로 자동화하세요",
            "🎬"
        )
        layout.addWidget(header)
        
        # 메인 영역 (스플리터)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 왼쪽: 매크로 목록
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        list_header = QHBoxLayout()
        list_header.addWidget(QLabel("매크로 목록"))
        list_header.addStretch()

        preset_btn = QPushButton("프리셋 추가")
        preset_btn.setProperty("class", "secondary")
        preset_btn.clicked.connect(self._add_preset_macro)
        list_header.addWidget(preset_btn)

        self.record_start_btn = QPushButton("녹화 시작")
        self.record_start_btn.setProperty("class", "secondary")
        self.record_start_btn.clicked.connect(self._start_recording)
        list_header.addWidget(self.record_start_btn)

        self.record_stop_btn = QPushButton("녹화 종료/저장")
        self.record_stop_btn.setProperty("class", "secondary")
        self.record_stop_btn.clicked.connect(self._stop_recording_and_save)
        list_header.addWidget(self.record_stop_btn)
        
        new_btn = QPushButton("+ 새 매크로")
        new_btn.clicked.connect(self._create_macro)
        list_header.addWidget(new_btn)
        
        left_layout.addLayout(list_header)
        
        self.macro_list = QListWidget()
        self.macro_list.currentItemChanged.connect(self._on_macro_selected)
        left_layout.addWidget(self.macro_list)
        
        splitter.addWidget(left_panel)
        
        # 오른쪽: 매크로 상세
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 0, 0, 0)
        
        self.detail_title = QLabel("매크로를 선택하세요")
        self.detail_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        right_layout.addWidget(self.detail_title)
        
        self.detail_desc = QLabel("")
        self.detail_desc.setStyleSheet("color: #888888;")
        right_layout.addWidget(self.detail_desc)
        
        right_layout.addSpacing(16)
        
        # 액션 목록
        right_layout.addWidget(QLabel("액션 목록:"))
        
        self.action_list = QListWidget()
        self.action_list.setMaximumHeight(200)
        right_layout.addWidget(self.action_list)
        
        # 스크립트 미리보기
        right_layout.addWidget(QLabel("Python 스크립트:"))
        
        self.script_preview = QTextEdit()
        self.script_preview.setReadOnly(True)
        self.script_preview.setFont(QFont("Consolas", 10))
        self.script_preview.setStyleSheet("""
            QTextEdit {
                background-color: #0f3460;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        right_layout.addWidget(self.script_preview)

        # 진행률 카드
        self.progress_card = ProgressCard()
        self.progress_card.setVisible(False)
        right_layout.addWidget(self.progress_card)
        
        # 버튼들
        btn_layout = QHBoxLayout()
        
        self.run_btn = QPushButton("▶ 실행")
        self.run_btn.clicked.connect(self._run_macro)
        self.run_btn.setEnabled(False)
        btn_layout.addWidget(self.run_btn)
        
        self.export_btn = QPushButton("📤 내보내기")
        self.export_btn.clicked.connect(self._export_macro)
        self.export_btn.setEnabled(False)
        btn_layout.addWidget(self.export_btn)
        
        btn_layout.addStretch()
        
        self.delete_btn = QPushButton("🗑️ 삭제")
        self.delete_btn.setProperty("class", "secondary")
        self.delete_btn.clicked.connect(self._delete_macro)
        self.delete_btn.setEnabled(False)
        btn_layout.addWidget(self.delete_btn)
        
        right_layout.addLayout(btn_layout)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 500])
        
        layout.addWidget(splitter)

    def _sync_recording_ui(self) -> None:
        recording = self._recorder.is_recording
        self.record_start_btn.setEnabled(not recording)
        self.record_stop_btn.setEnabled(recording)

    def _start_recording(self) -> None:
        if self._recorder.is_recording:
            QMessageBox.information(self, "안내", "이미 매크로 녹화 중입니다.")
            self._sync_recording_ui()
            return
        self._recorder.start_recording()
        self._sync_recording_ui()
        QMessageBox.information(
            self,
            "녹화 시작",
            "매크로 녹화를 시작했습니다.\nAction Console 실행 명령이 녹화됩니다.",
        )

    def _stop_recording_and_save(self) -> None:
        if not self._recorder.is_recording:
            QMessageBox.information(self, "안내", "현재 진행 중인 녹화가 없습니다.")
            self._sync_recording_ui()
            return

        actions = self._recorder.stop_recording()
        self._sync_recording_ui()
        if not actions:
            QMessageBox.information(self, "안내", "기록된 액션이 없습니다.")
            return

        default_name = "녹화 매크로"
        name, ok = QInputDialog.getText(self, "매크로 저장", "매크로 이름:", text=default_name)
        if not ok:
            return
        macro_name = str(name).strip() or default_name
        description = "Action Console 실행 흐름에서 녹화된 매크로"

        try:
            self._recorder.save_macro(macro_name, actions, description=description)
            self._load_macros()
            QMessageBox.information(self, "완료", f"매크로가 저장되었습니다.\n이름: {macro_name}\n액션: {len(actions)}개")
        except Exception as e:
            QMessageBox.warning(self, "오류", f"매크로 저장 실패:\n{e}")

    def _add_preset_macro(self) -> None:
        presets = self._recorder.get_preset_macros()
        if not presets:
            QMessageBox.information(self, "알림", "사용 가능한 프리셋이 없습니다.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("프리셋 매크로 추가")
        dialog.setFixedSize(520, 420)

        v = QVBoxLayout(dialog)
        v.addWidget(QLabel("추가할 프리셋을 선택하세요"))

        lst = QListWidget()
        for p in presets:
            item = QListWidgetItem(f"{p.get('name')} - {p.get('description')}")
            item.setData(Qt.ItemDataRole.UserRole, p)
            lst.addItem(item)
        v.addWidget(lst, 1)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel = QPushButton("취소")
        cancel.setProperty("class", "secondary")
        cancel.clicked.connect(dialog.reject)
        btns.addWidget(cancel)

        ok = QPushButton("추가")
        ok.clicked.connect(dialog.accept)
        btns.addWidget(ok)
        v.addLayout(btns)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        current = lst.currentItem()
        if not current:
            return
        preset = current.data(Qt.ItemDataRole.UserRole) or {}

        name = preset.get("name", "프리셋 매크로")
        replacements = preset.get("replacements", [])
        if not replacements:
            QMessageBox.warning(self, "오류", "프리셋 데이터가 비어있습니다.")
            return

        try:
            self._recorder.create_batch_replace_macro(
                name=name,
                replacements=[tuple(r) for r in replacements],
                description=preset.get("description", ""),
            )
            self._load_macros()
            QMessageBox.information(self, "완료", f"'{name}' 프리셋 매크로가 추가되었습니다.")
        except Exception as e:
            QMessageBox.warning(self, "오류", f"프리셋 추가 실패:\n{e}")
    
    def _load_macros(self) -> None:
        """매크로 목록 로드"""
        self.macro_list.clear()
        
        for macro in self._recorder.get_all_macros():
            item = MacroListItem(macro)
            self.macro_list.addItem(item)
        
        if self.macro_list.count() == 0:
            empty_item = QListWidgetItem("매크로가 없습니다")
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.macro_list.addItem(empty_item)
    
    def _on_macro_selected(self, current: QListWidgetItem, previous: QListWidgetItem) -> None:
        """매크로 선택"""
        if not current or not isinstance(current, MacroListItem):
            self._clear_detail()
            return
        
        macro = current.macro
        
        self.detail_title.setText(macro.name)
        self.detail_desc.setText(f"{macro.description}\n실행 횟수: {macro.run_count}")
        
        # 액션 목록
        self.action_list.clear()
        for action in macro.actions:
            desc = action.description or action.action_type
            self.action_list.addItem(f"• {desc}")
        
        # 스크립트 미리보기
        self.script_preview.setPlainText(macro.to_python_script())
        
        # 버튼 활성화
        self.run_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
    
    def _clear_detail(self) -> None:
        """상세 정보 초기화"""
        self.detail_title.setText("매크로를 선택하세요")
        self.detail_desc.setText("")
        self.action_list.clear()
        self.script_preview.clear()
        self.run_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
    
    def _create_macro(self) -> None:
        """매크로 생성"""
        dialog = CreateMacroDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            
            if not data["name"]:
                QMessageBox.warning(self, "오류", "매크로 이름을 입력해주세요.")
                return
            
            if data["type"] == 0:  # 찾기/바꾸기
                if not data["find"]:
                    QMessageBox.warning(self, "오류", "찾을 텍스트를 입력해주세요.")
                    return
                
                self._recorder.create_quick_macro(
                    name=data["name"],
                    find_text=data["find"],
                    replace_text=data["replace"],
                    description=data["description"]
                )
            
            elif data["type"] == 1:  # 서식 변경
                self._recorder.create_format_macro(
                    name=data["name"],
                    bold=data["bold"],
                    italic=data["italic"],
                    underline=data["underline"],
                    color=data["color"],
                    size=data["size"],
                    description=data["description"]
                )
            
            else:  # 빈 매크로
                self._recorder.save_macro(
                    name=data["name"],
                    actions=[],
                    description=data["description"]
                )
            
            self._load_macros()
            QMessageBox.information(self, "완료", "매크로가 생성되었습니다.")
    
    def _run_macro(self) -> None:
        """매크로 실행"""
        current = self.macro_list.currentItem()
        if not current or not isinstance(current, MacroListItem):
            return
        
        macro = current.macro
        
        reply = QMessageBox.question(
            self,
            "매크로 실행",
            f"'{macro.name}' 매크로를 실행하시겠습니까?\n\n"
            "주의: 한글 프로그램이 제어됩니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self._worker is not None:
                try:
                    self.progress_card.cancelled.disconnect(self._worker.cancel)
                except TypeError:
                    pass

            self.progress_card.setVisible(True)
            self.progress_card.reset()
            self.progress_card.set_status("매크로 실행 중...")
            self.run_btn.setEnabled(False)
            self.export_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            self._running_macro_id = macro.id
            self._running_macro_name = macro.name

            self._worker = MacroRunWorker(macro.id)
            self.progress_card.cancelled.connect(self._worker.cancel)
            self._worker.progress.connect(lambda c, t, n: (self.progress_card.set_count(c, t), self.progress_card.set_current_file(n)))
            self._worker.status_changed.connect(self.progress_card.set_status)
            self._worker.finished_with_result.connect(self._on_run_finished)
            self._worker.error_occurred.connect(self._on_run_error)
            self._worker.start()

    def _on_run_finished(self, result: WorkerResult) -> None:
        self.run_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)

        data = result.data or {}
        if data.get("cancelled"):
            self.progress_card.set_error("작업이 취소되었습니다.")
            return

        record_task_result(
            TaskType.MACRO,
            f"매크로 실행: {getattr(self, '_running_macro_name', '') or '매크로'}",
            [],
            result,
            options={
                "macro_id": getattr(self, "_running_macro_id", ""),
                "macro_name": getattr(self, "_running_macro_name", ""),
            },
            settings=self._settings,
        )

        if result.success:
            self.progress_card.set_completed(1, 0)
            self._load_macros()
            QMessageBox.information(self, "완료", "매크로 실행이 완료되었습니다.")
        else:
            self.progress_card.set_error(result.error_message or "오류 발생")
            QMessageBox.warning(self, "오류", result.error_message or "매크로 실행에 실패했습니다.")

    def _on_run_error(self, message: str) -> None:
        self.run_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        self.progress_card.set_error(message)
    
    def _export_macro(self) -> None:
        """매크로 내보내기"""
        current = self.macro_list.currentItem()
        if not current or not isinstance(current, MacroListItem):
            return
        
        macro = current.macro
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "매크로 스크립트 저장",
            str(Path(self._settings.get("default_output_dir", str(Path.home() / "Documents"))) / f"{macro.name}.py"),
            "Python 파일 (*.py)"
        )
        
        if file_path:
            if self._recorder.export_macro(macro.id, file_path):
                track_recent_files([file_path], settings=self._settings)
                QMessageBox.information(self, "완료", f"스크립트가 저장되었습니다:\n{file_path}")
            else:
                QMessageBox.warning(self, "오류", "스크립트 저장에 실패했습니다.")
    
    def _delete_macro(self) -> None:
        """매크로 삭제"""
        current = self.macro_list.currentItem()
        if not current or not isinstance(current, MacroListItem):
            return
        
        macro = current.macro
        
        reply = QMessageBox.question(
            self,
            "매크로 삭제",
            f"'{macro.name}' 매크로를 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._recorder.delete_macro(macro.id)
            self._load_macros()
            self._clear_detail()

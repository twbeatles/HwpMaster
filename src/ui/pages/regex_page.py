"""
Regex Page
정규식 치환기 UI

Author: HWP Master
"""

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit,
    QFrame, QComboBox, QCheckBox, QListWidget,
    QListWidgetItem, QFileDialog, QMessageBox, QGroupBox,
    QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from ...core.regex_replacer import RegexReplacer, ReplacementRule
from ...utils.history_manager import TaskType
from ..widgets.file_list import FileListWidget
from ..widgets.progress_card import ProgressCard
from ..widgets.page_header import PageHeader
from ...utils.worker import RegexReplaceWorker, WorkerResult
from ...utils.settings import get_settings_manager
from ...utils.task_tracking import record_task_result


class PresetCard(QFrame):
    """프리셋 카드"""
    
    clicked = Signal(str)  # preset_id
    
    def __init__(
        self,
        preset_id: str,
        rule: ReplacementRule,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.preset_id = preset_id
        self.rule = rule
        self.setProperty("class", "card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(140)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        
        # 이름
        name_label = QLabel(rule.name)
        name_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        name_label.setWordWrap(True)
        layout.addWidget(name_label)
        
        # 설명
        desc_label = QLabel(rule.description)
        desc_label.setStyleSheet("color: #bbbbbb; font-size: 11px;")
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(desc_label)
    
    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self.preset_id)
        super().mousePressEvent(event)


class RegexPage(QWidget):
    """정규식 치환기 페이지"""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        
        self._replacer = RegexReplacer()
        self._selected_rules: list[ReplacementRule] = []
        self._worker: Optional[RegexReplaceWorker] = None
        self._settings = get_settings_manager()
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # 페이지 헤더
        header = PageHeader(
            "정규식 치환기",
            "패턴 기반으로 텍스트를 찾아 치환합니다 (민감정보 마스킹 등)",
            "🔤"
        )
        layout.addWidget(header)
        
        # 메인 영역 (2컬럼)
        main_layout = QHBoxLayout()
        main_layout.setSpacing(24)
        
        # 왼쪽: 프리셋 + 커스텀
        left_panel = QVBoxLayout()
        left_panel.setSpacing(16)
        
        # 프리셋 섹션
        # 프리셋 섹션
        preset_group = QGroupBox("🎯 마스킹 프리셋")
        group_layout = QVBoxLayout(preset_group)
        
        # 스크롤 영역
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                border: none;
                background: #2d2d2d;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                border-radius: 4px;
            }
        """)
        scroll_area.setMinimumHeight(350)  # 최소 높이 설정
        
        scroll_content = QWidget()
        scroll_layout = QGridLayout(scroll_content)
        scroll_layout.setSpacing(8)
        scroll_layout.setContentsMargins(0, 0, 10, 0)  # 스크롤바 여백
        
        presets = list(self._replacer.PRESETS.items())
        cols = 2
        for idx, (preset_id, rule) in enumerate(presets):  # 모든 프리셋 표시
            card = PresetCard(preset_id, rule)
            card.clicked.connect(self._on_preset_clicked)
            row = idx // cols
            col = idx % cols
            scroll_layout.addWidget(card, row, col)
            
        scroll_area.setWidget(scroll_content)
        group_layout.addWidget(scroll_area)
        
        left_panel.addWidget(preset_group)
        
        # 커스텀 규칙 입력
        custom_group = QGroupBox("✏️ 커스텀 규칙")
        custom_layout = QVBoxLayout(custom_group)
        
        # 패턴 입력
        pattern_layout = QHBoxLayout()
        pattern_layout.addWidget(QLabel("패턴:"))
        self.pattern_edit = QLineEdit()
        self.pattern_edit.setPlaceholderText(r"예: (\d{6})-(\d{7})")
        self.pattern_edit.textChanged.connect(self._validate_pattern)
        pattern_layout.addWidget(self.pattern_edit)
        custom_layout.addLayout(pattern_layout)
        
        # 치환 입력
        replace_layout = QHBoxLayout()
        replace_layout.addWidget(QLabel("치환:"))
        self.replace_edit = QLineEdit()
        self.replace_edit.setPlaceholderText(r"예: \1-*******")
        replace_layout.addWidget(self.replace_edit)
        custom_layout.addLayout(replace_layout)
        
        # 옵션
        option_layout = QHBoxLayout()
        self.regex_check = QCheckBox("정규식 사용")
        self.regex_check.setChecked(True)
        option_layout.addWidget(self.regex_check)
        
        self.case_check = QCheckBox("대소문자 구분")
        option_layout.addWidget(self.case_check)
        
        option_layout.addStretch()
        
        add_rule_btn = QPushButton("규칙 추가")
        add_rule_btn.clicked.connect(self._add_custom_rule)
        option_layout.addWidget(add_rule_btn)
        
        custom_layout.addLayout(option_layout)
        
        # 패턴 유효성 표시
        self.pattern_status = QLabel("")
        self.pattern_status.setStyleSheet("font-size: 11px;")
        custom_layout.addWidget(self.pattern_status)
        
        left_panel.addWidget(custom_group)
        
        main_layout.addLayout(left_panel, stretch=1)
        
        # 오른쪽: 파일 목록 + 선택된 규칙
        right_panel = QVBoxLayout()
        right_panel.setSpacing(16)
        
        # 선택된 규칙
        rules_group = QGroupBox("📋 적용할 규칙")
        rules_layout = QVBoxLayout(rules_group)
        
        self.rules_list = QListWidget()
        self.rules_list.setMaximumHeight(120)
        rules_layout.addWidget(self.rules_list)
        
        rules_btn_layout = QHBoxLayout()
        rules_btn_layout.addStretch()
        
        clear_rules_btn = QPushButton("전체 삭제")
        clear_rules_btn.setProperty("class", "secondary")
        clear_rules_btn.clicked.connect(self._clear_rules)
        rules_btn_layout.addWidget(clear_rules_btn)
        
        rules_layout.addLayout(rules_btn_layout)
        
        right_panel.addWidget(rules_group)
        
        # 파일 목록
        files_group = QGroupBox("📁 대상 파일")
        files_layout = QVBoxLayout(files_group)
        
        self.file_list = FileListWidget()
        files_layout.addWidget(self.file_list)
        
        right_panel.addWidget(files_group)
        
        # 진행률
        self.progress_card = ProgressCard()
        self.progress_card.setVisible(False)
        right_panel.addWidget(self.progress_card)
        
        # 실행 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.preview_btn = QPushButton("미리보기")
        self.preview_btn.setProperty("class", "secondary")
        self.preview_btn.clicked.connect(self._preview)
        btn_layout.addWidget(self.preview_btn)
        
        self.execute_btn = QPushButton("치환 실행")
        self.execute_btn.setMinimumWidth(120)
        self.execute_btn.clicked.connect(self._execute)
        btn_layout.addWidget(self.execute_btn)
        
        right_panel.addLayout(btn_layout)
        
        main_layout.addLayout(right_panel, stretch=1)
        
        layout.addLayout(main_layout)
    
    def _validate_pattern(self, text: str) -> None:
        """패턴 유효성 검사"""
        if not text:
            self.pattern_status.setText("")
            return
        
        is_valid, error = self._replacer.validate_pattern(text)
        
        if is_valid:
            self.pattern_status.setText("✅ 유효한 정규식입니다")
            self.pattern_status.setStyleSheet("color: #28a745; font-size: 11px;")
        else:
            self.pattern_status.setText(f"❌ 오류: {error}")
            self.pattern_status.setStyleSheet("color: #dc3545; font-size: 11px;")
    
    def _on_preset_clicked(self, preset_id: str) -> None:
        """프리셋 클릭"""
        rule = self._replacer.get_preset(preset_id)
        if rule:
            self._add_rule(rule)
    
    def _add_custom_rule(self) -> None:
        """커스텀 규칙 추가"""
        pattern = self.pattern_edit.text()
        replacement = self.replace_edit.text()
        
        if not pattern:
            QMessageBox.warning(self, "오류", "패턴을 입력해주세요.")
            return
        
        # 유효성 검사
        if self.regex_check.isChecked():
            is_valid, error = self._replacer.validate_pattern(pattern)
            if not is_valid:
                QMessageBox.warning(self, "오류", f"잘못된 정규식입니다:\n{error}")
                return
        
        rule = ReplacementRule(
            name=f"커스텀: {pattern[:20]}...",
            pattern=pattern,
            replacement=replacement,
            is_regex=self.regex_check.isChecked(),
            case_sensitive=self.case_check.isChecked()
        )
        
        self._add_rule(rule)
        
        # 입력 필드 초기화
        self.pattern_edit.clear()
        self.replace_edit.clear()
        self.pattern_status.clear()
    
    def _add_rule(self, rule: ReplacementRule) -> None:
        """규칙 추가"""
        self._selected_rules.append(rule)
        
        item = QListWidgetItem(f"✅ {rule.name}")
        item.setData(Qt.ItemDataRole.UserRole, rule)
        self.rules_list.addItem(item)
    
    def _clear_rules(self) -> None:
        """규칙 전체 삭제"""
        self._selected_rules.clear()
        self.rules_list.clear()
    
    def _preview(self) -> None:
        """미리보기"""
        if not self._selected_rules:
            QMessageBox.warning(self, "오류", "적용할 규칙을 선택해주세요.")
            return
        
        # 테스트 텍스트로 미리보기
        test_text = """
홍길동 (123456-1234567)
연락처: 010-1234-5678
이메일: test@example.com
카드번호: 1234-5678-9012-3456
"""
        
        result_lines = ["[미리보기 결과]", "", f"원본:", test_text, "", "치환 후:"]
        
        current_text = test_text
        for rule in self._selected_rules:
            current_text, count = self._replacer.replace_text(current_text, rule)
            if count > 0:
                result_lines.append(f"  - {rule.name}: {count}건 치환")
        
        result_lines.append("")
        result_lines.append(current_text)
        
        QMessageBox.information(self, "미리보기", "\n".join(result_lines))
    
    def _execute(self) -> None:
        """치환 실행"""
        files = self.file_list.get_files()
        
        if not files:
            QMessageBox.warning(self, "오류", "대상 파일을 추가해주세요.")
            return
        
        if not self._selected_rules:
            QMessageBox.warning(self, "오류", "적용할 규칙을 선택해주세요.")
            return
        
        # 출력 디렉토리 선택
        output_dir = QFileDialog.getExistingDirectory(
            self,
            "저장 위치 선택",
            self._settings.get("default_output_dir", str(Path.home() / "Documents"))
        )
        
        if not output_dir:
            return
        
        self.progress_card.setVisible(True)
        self.progress_card.set_status("치환 진행 중...")
        self.progress_card.reset()
        self.execute_btn.setEnabled(False)
        self.preview_btn.setEnabled(False)
        
        # Worker로 실행 (UI 블로킹 방지)
        if self._worker is not None:
            try:
                self.progress_card.cancelled.disconnect(self._worker.cancel)
            except TypeError:
                pass

        self._worker = RegexReplaceWorker(files, self._selected_rules, output_dir)
        self.progress_card.cancelled.connect(self._worker.cancel)
        self._worker.progress.connect(lambda c, t, n: (self.progress_card.set_count(c, t), self.progress_card.set_current_file(n)))
        self._worker.status_changed.connect(self.progress_card.set_status)
        self._worker.finished_with_result.connect(self._on_execute_finished)
        self._worker.error_occurred.connect(self._on_execute_error)
        self._worker.start()

    def _on_execute_finished(self, result: WorkerResult) -> None:
        self.execute_btn.setEnabled(True)
        self.preview_btn.setEnabled(True)

        data = result.data or {}
        if data.get("cancelled"):
            self.progress_card.set_error("작업이 취소되었습니다.")
            return

        record_task_result(
            TaskType.REGEX,
            "정규식 치환",
            self.file_list.get_files(),
            result,
            options={"rule_count": len(self._selected_rules)},
            settings=self._settings,
        )

        if result.success:
            success_count = data.get("success_count", 0)
            fail_count = data.get("fail_count", 0)
            total_replaced = data.get("total_replaced", 0)
            total_replaced_known = data.get("total_replaced_known", True)
            output_dir = data.get("output_dir", "")

            self.progress_card.set_completed(success_count, fail_count)
            replaced_line = (
                f"총 치환: {total_replaced}건\n"
                if total_replaced_known
                else f"총 치환(최소): {total_replaced}건 (정확 집계 미지원)\n"
            )
            QMessageBox.information(
                self,
                "완료",
                f"치환이 완료되었습니다.\n\n"
                f"처리 파일: {success_count + fail_count}개 (성공: {success_count}, 실패: {fail_count})\n"
                f"{replaced_line}"
                f"저장 위치: {output_dir}"
            )
        else:
            self.progress_card.set_error(result.error_message or "오류 발생")
            QMessageBox.warning(self, "오류", result.error_message or "치환 중 오류가 발생했습니다.")

    def _on_execute_error(self, message: str) -> None:
        self.progress_card.set_error(message)
        self.execute_btn.setEnabled(True)
        self.preview_btn.setEnabled(True)

"""
Template Page
스마트 템플릿 스토어 UI

Author: HWP Master
"""

from pathlib import Path
from typing import Optional, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QComboBox,
    QFrame, QScrollArea, QFileDialog, QMessageBox,
    QDialog, QFormLayout, QTextEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from ...core.template_store import TemplateStore, TemplateInfo, TemplateStoreError
from ..widgets.page_header import PageHeader
from ...utils.history_manager import TaskType
from ...utils.settings import get_settings_manager
from ...utils.task_tracking import record_task_summary


def _template_output_suffix(template: TemplateInfo) -> str:
    suffix = Path(template.file_path).suffix if template.file_path else ""
    return suffix or ".hwp"


def _template_output_filter(template: TemplateInfo) -> str:
    suffix = _template_output_suffix(template).lower()
    if suffix == ".hwpx":
        return "HWPX 파일 (*.hwpx)"
    return "HWP 파일 (*.hwp)"


def _template_output_path(template: TemplateInfo, base_dir: str) -> str:
    return str(Path(base_dir) / f"{template.name}{_template_output_suffix(template)}")


class TemplateCard(QFrame):
    """템플릿 카드 위젯"""
    
    clicked = Signal(str)  # template_id
    favorite_toggled = Signal(str)  # template_id
    delete_requested = Signal(str)  # template_id
    
    def __init__(
        self,
        template: TemplateInfo,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.template = template
        self.setProperty("class", "card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(220, 180)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        
        # 상단: 카테고리 뱃지 + 즐겨찾기
        header = QHBoxLayout()
        
        category_label = QLabel(template.category)
        category_label.setStyleSheet("""
            background-color: #533483;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
        """)
        header.addWidget(category_label)
        
        header.addStretch()
        
        self.fav_btn = QPushButton("★" if template.is_favorite else "☆")
        self.fav_btn.setFixedSize(28, 28)
        self.fav_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-size: 18px;
                color: #ffc107;
            }
            QPushButton:hover {
                background-color: rgba(255, 193, 7, 0.2);
                border-radius: 14px;
            }
        """)
        self.fav_btn.clicked.connect(self._on_favorite_clicked)
        header.addWidget(self.fav_btn)
        
        # 삭제 버튼 (사용자 템플릿만)
        if not template.is_builtin:
            self.del_btn = QPushButton("×")
            self.del_btn.setFixedSize(28, 28)
            self.del_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    font-size: 18px;
                    color: #dc3545;
                }
                QPushButton:hover {
                    background-color: rgba(220, 53, 69, 0.2);
                    border-radius: 14px;
                }
            """)
            self.del_btn.clicked.connect(self._on_delete_clicked)
            header.addWidget(self.del_btn)
        
        layout.addLayout(header)
        
        # 아이콘
        icon_label = QLabel("📄")
        icon_label.setStyleSheet("font-size: 32px;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # 이름
        name_label = QLabel(template.name)
        name_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setWordWrap(True)
        layout.addWidget(name_label)
        
        # 설명
        desc_label = QLabel(template.description[:40] + "..." if len(template.description) > 40 else template.description)
        desc_label.setStyleSheet("color: #888888; font-size: 11px;")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        layout.addStretch()
    
    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self.template.id)
        super().mousePressEvent(event)
    
    def _on_favorite_clicked(self) -> None:
        self.favorite_toggled.emit(self.template.id)
    
    def update_favorite(self, is_favorite: bool) -> None:
        self.fav_btn.setText("★" if is_favorite else "☆")
        self.template.is_favorite = is_favorite
    
    def _on_delete_clicked(self) -> None:
        self.delete_requested.emit(self.template.id)


class AddTemplateDialog(QDialog):
    """템플릿 추가 다이얼로그"""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("사용자 템플릿 추가")
        self.setFixedSize(450, 350)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        form = QFormLayout()
        
        # 이름
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("템플릿 이름 입력")
        form.addRow("이름:", self.name_edit)
        
        # 파일 선택
        file_layout = QHBoxLayout()
        self.file_edit = QLineEdit()
        self.file_edit.setReadOnly(True)
        self.file_edit.setPlaceholderText("HWP 파일을 선택하세요")
        file_layout.addWidget(self.file_edit)
        
        browse_btn = QPushButton("찾아보기...")
        browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(browse_btn)
        
        form.addRow("파일:", file_layout)
        
        # 카테고리
        self.category_combo = QComboBox()
        self.category_combo.addItems(["휴가", "지출", "회의", "보고서", "계약", "공문", "기타"])
        form.addRow("카테고리:", self.category_combo)
        
        # 설명
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(80)
        self.desc_edit.setPlaceholderText("템플릿 설명 (선택사항)")
        form.addRow("설명:", self.desc_edit)
        
        layout.addLayout(form)
        layout.addStretch()
        
        # 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("취소")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        self.add_btn = QPushButton("추가")
        self.add_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.add_btn)
        
        layout.addLayout(btn_layout)
    
    def _browse_file(self) -> None:
        default_dir = get_settings_manager().get("default_output_dir", "")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "템플릿 파일 선택",
            default_dir,
            "HWP 파일 (*.hwp *.hwpx)"
        )
        if file_path:
            self.file_edit.setText(file_path)
    
    def get_data(self) -> dict[str, Any]:
        return {
            "name": self.name_edit.text(),
            "file_path": self.file_edit.text(),
            "category": self.category_combo.currentText(),
            "description": self.desc_edit.toPlainText()
        }


class TemplateFieldDialog(QDialog):
    """템플릿 필드 입력 다이얼로그."""

    def __init__(self, template: TemplateInfo, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._template = template
        self._field_edits: dict[str, QLineEdit] = {}
        self.setWindowTitle(f"{template.name} 입력값")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        guide = QLabel("템플릿 필드 값을 입력하세요. 빈 값은 빈 문자열로 처리됩니다.")
        guide.setWordWrap(True)
        guide.setStyleSheet("color: #888888;")
        layout.addWidget(guide)

        form = QFormLayout()
        for field_name in template.fields:
            edit = QLineEdit()
            edit.setPlaceholderText(field_name)
            self._field_edits[field_name] = edit
            form.addRow(f"{field_name}:", edit)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("취소")
        cancel_btn.setProperty("class", "secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        ok_btn = QPushButton("생성")
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)

        layout.addLayout(btn_layout)

    def get_data(self) -> dict[str, str]:
        return {name: edit.text() for name, edit in self._field_edits.items()}


class TemplatePage(QWidget):
    """템플릿 스토어 페이지"""
    
    template_selected = Signal(str, dict)  # template_id, template_info
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        
        self._store = TemplateStore()
        self._current_category = "전체"
        self._settings = get_settings_manager()
        
        self._setup_ui()
        self._load_templates()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # 페이지 헤더
        page_header = PageHeader(
            "스마트 템플릿 스토어",
            "자주 사용하는 공문서 양식을 클릭 한 번으로 불러오세요",
            "📦"
        )
        layout.addWidget(page_header)
        
        # 필터 영역
        filter_layout = QHBoxLayout()
        
        # 검색
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 템플릿 검색...")
        self.search_edit.setMinimumWidth(250)
        self.search_edit.textChanged.connect(self._on_search)
        filter_layout.addWidget(self.search_edit)
        
        filter_layout.addStretch()
        
        # 카테고리 필터
        filter_layout.addWidget(QLabel("카테고리:"))
        self.category_combo = QComboBox()
        self.category_combo.addItem("전체")
        self.category_combo.addItems(self._store.get_categories())
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        filter_layout.addWidget(self.category_combo)
        
        # 추가 버튼
        add_btn = QPushButton("+ 사용자 템플릿 추가")
        add_btn.clicked.connect(self._add_template)
        filter_layout.addWidget(add_btn)
        
        layout.addLayout(filter_layout)
        
        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self._grid_container = QWidget()
        self._grid_layout = QGridLayout(self._grid_container)
        self._grid_layout.setSpacing(16)
        self._grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        scroll.setWidget(self._grid_container)
        layout.addWidget(scroll)
    
    def _load_templates(self) -> None:
        """템플릿 로드 및 표시"""
        # 기존 카드 제거
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        
        # 템플릿 가져오기
        if self._current_category == "전체":
            templates = self._store.get_all_templates()
        else:
            templates = self._store.get_templates_by_category(self._current_category)
        
        # 검색 필터
        search_text = self.search_edit.text().lower()
        if search_text:
            templates = [
                t for t in templates
                if search_text in t.name.lower() or search_text in t.description.lower()
            ]
        
        # 카드 생성
        cols = 4
        for idx, template in enumerate(templates):
            card = TemplateCard(template)
            card.clicked.connect(self._on_template_clicked)
            card.favorite_toggled.connect(self._on_favorite_toggled)
            card.delete_requested.connect(self._on_template_delete)
            
            row = idx // cols
            col = idx % cols
            self._grid_layout.addWidget(card, row, col)
        
        # 빈 상태 표시
        if not templates:
            empty_label = QLabel("템플릿이 없습니다")
            empty_label.setStyleSheet("color: #666666; font-size: 16px;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._grid_layout.addWidget(empty_label, 0, 0, 1, cols)
    
    def _on_search(self, text: str) -> None:
        """검색"""
        self._load_templates()
    
    def _on_category_changed(self, category: str) -> None:
        """카테고리 변경"""
        self._current_category = category
        self._load_templates()

    def _prompt_template_fields(self, template: TemplateInfo) -> Optional[dict[str, str]]:
        dialog = TemplateFieldDialog(template, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return dialog.get_data()
    
    def _on_template_clicked(self, template_id: str) -> None:
        """템플릿 클릭"""
        template = self._store.get_template(template_id)
        if template:
            try:
                # 내장 템플릿이지만 파일이 없으면 먼저 등록 플로우로 유도 (README 가이드와 정합)
                if template.is_builtin and (not template.file_path or not Path(template.file_path).exists()):
                    QMessageBox.information(
                        self,
                        "파일 등록 필요",
                        f"'{template.name}' 템플릿을 사용하려면 HWP 파일을 먼저 등록해야 합니다.",
                    )
                    hwp_path, _ = QFileDialog.getOpenFileName(
                        self,
                        "템플릿 파일 선택",
                        self._settings.get("default_output_dir", str(Path.home() / "Documents")),
                        "HWP 파일 (*.hwp *.hwpx)",
                    )
                    if not hwp_path:
                        return

                    ok = self._store.register_builtin_template_file(template_id, hwp_path)
                    if not ok:
                        QMessageBox.warning(self, "오류", "템플릿 파일 등록에 실패했습니다.")
                        return

                    self._load_templates()
                    template = self._store.get_template(template_id)
                    if template is None or not template.file_path:
                        QMessageBox.warning(self, "오류", "템플릿 등록 후 정보를 불러오지 못했습니다.")
                        return

                file_path, _ = QFileDialog.getSaveFileName(
                    self,
                    "저장 위치 선택",
                    _template_output_path(
                        template,
                        self._settings.get("default_output_dir", str(Path.home() / "Documents")),
                    ),
                    _template_output_filter(template),
                )
                if not file_path:
                    return

                creation_mode = "copy"
                if template.fields:
                    field_values = self._prompt_template_fields(template)
                    if field_values is None:
                        return
                    creation_mode = "field_injection"
                    result = self._store.create_from_template(template_id, field_values, file_path)
                else:
                    result = self._store.use_template(template_id, file_path)

                if result:
                    self.template_selected.emit(template_id, template.to_dict())
                    record_task_summary(
                        TaskType.TEMPLATE,
                        f"템플릿 생성: {template.name}",
                        [result],
                        success_count=1,
                        fail_count=0,
                        options={
                            "template_id": template.id,
                            "template_name": template.name,
                            "mode": creation_mode,
                        },
                        settings=self._settings,
                        recent_files=[result],
                    )
                    QMessageBox.information(
                        self,
                        "완료",
                        f"'{template.name}' 템플릿이 생성되었습니다.\n\n"
                        f"저장 위치: {result}\n"
                        f"필드: {', '.join(template.fields) if template.fields else '없음'}"
                    )
                else:
                    QMessageBox.warning(self, "오류", "템플릿 생성에 실패했습니다.")
            except ValueError as e:
                QMessageBox.warning(self, "템플릿 오류", str(e))
            except TemplateStoreError as e:
                QMessageBox.warning(self, "템플릿 저장소 오류", str(e))
            except Exception as e:
                QMessageBox.warning(self, "오류", f"템플릿 생성 중 오류가 발생했습니다:\n{e}")
    
    def _on_favorite_toggled(self, template_id: str) -> None:
        """즐겨찾기 토글"""
        is_favorite = self._store.toggle_favorite(template_id)
        
        # 카드 업데이트
        for i in range(self._grid_layout.count()):
            item = self._grid_layout.itemAt(i)
            if item and item.widget():
                card = item.widget()
                if isinstance(card, TemplateCard) and card.template.id == template_id:
                    card.update_favorite(is_favorite)
                    break
    
    def _on_template_delete(self, template_id: str) -> None:
        """템플릿 삭제"""
        template = self._store.get_template(template_id)
        if not template:
            return
        
        # 확인 다이얼로그
        reply = QMessageBox.question(
            self,
            "템플릿 삭제",
            f"'{template.name}' 템플릿을 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if self._store.remove_template(template_id):
                    self._load_templates()
                    QMessageBox.information(self, "완료", "템플릿이 삭제되었습니다.")
                else:
                    QMessageBox.warning(self, "오류", "템플릿 삭제에 실패했습니다.")
            except TemplateStoreError as e:
                QMessageBox.warning(self, "템플릿 저장소 오류", str(e))
    
    def _add_template(self) -> None:
        """사용자 템플릿 추가"""
        dialog = AddTemplateDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            
            if not data["name"] or not data["file_path"]:
                QMessageBox.warning(self, "오류", "이름과 파일을 입력해주세요.")
                return
            
            try:
                self._store.add_user_template(
                    name=data["name"],
                    file_path=data["file_path"],
                    description=data["description"],
                    category=data["category"]
                )
            except TemplateStoreError as e:
                QMessageBox.warning(self, "템플릿 저장소 오류", str(e))
                return

            self._load_templates()
            QMessageBox.information(self, "완료", "템플릿이 추가되었습니다.")

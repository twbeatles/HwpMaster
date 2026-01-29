"""
File List Widget
드래그 앤 드롭 파일 목록 위젯

Author: HWP Master
"""

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QListWidgetItem, QPushButton, QLabel, QFrame,
    QFileDialog, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDropEvent


class DropZone(QFrame):
    """드래그 앤 드롭 존"""
    
    files_dropped = Signal(list)  # list[str]
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(140)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.setStyleSheet("""
            #dropZone {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #161b22, stop:1 #0d1117);
                border: 2px dashed #30363d;
                border-radius: 16px;
            }
            #dropZone:hover {
                border-color: #8957e5;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(137, 87, 229, 0.1), stop:1 rgba(137, 87, 229, 0.05));
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)
        
        # 아이콘
        icon_label = QLabel("📂")
        icon_label.setStyleSheet("font-size: 42px; background: transparent;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # 안내 텍스트
        text_label = QLabel("파일을 여기에 끌어다 놓거나 클릭하여 선택")
        text_label.setStyleSheet("""
            color: #8b949e;
            font-size: 14px;
            font-weight: 500;
            background: transparent;
        """)
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(text_label)
        
        # 지원 포맷
        format_label = QLabel("HWP, HWPX 파일 지원")
        format_label.setStyleSheet("""
            color: #484f58;
            font-size: 12px;
            background: transparent;
        """)
        format_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(format_label)
    
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                #dropZone {
                    border: 2px dashed #8957e5;
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(137, 87, 229, 0.15), stop:1 rgba(137, 87, 229, 0.08));
                }
            """)
    
    def dragLeaveEvent(self, event) -> None:
        self.setStyleSheet("")
    
    def dropEvent(self, event: QDropEvent) -> None:
        self.setStyleSheet("")
        
        files: list[str] = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path:
                path = Path(file_path)
                if path.is_file():
                    files.append(file_path)
                elif path.is_dir():
                    # 디렉토리면 HWP 파일 검색
                    for hwp_file in path.rglob("*.hwp"):
                        files.append(str(hwp_file))
                    for hwpx_file in path.rglob("*.hwpx"):
                        files.append(str(hwpx_file))
        
        if files:
            self.files_dropped.emit(files)
    
    def mousePressEvent(self, event) -> None:
        # 클릭 시 파일 선택 다이얼로그
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "파일 선택",
            "",
            "HWP 파일 (*.hwp *.hwpx);;모든 파일 (*.*)"
        )
        if files:
            self.files_dropped.emit(files)


class FileListWidget(QWidget):
    """파일 목록 관리 위젯"""
    
    files_changed = Signal(list)  # list[str]
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        
        self._files: list[str] = []
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 드롭 존
        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self._on_files_dropped)
        layout.addWidget(self.drop_zone)
        
        # 파일 목록
        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_widget.setMinimumHeight(150)
        self.list_widget.model().rowsMoved.connect(self._on_order_changed)
        layout.addWidget(self.list_widget)
        
        # 버튼 영역
        btn_layout = QHBoxLayout()
        
        self.count_label = QLabel("0개 파일")
        self.count_label.setStyleSheet("color: #888888;")
        btn_layout.addWidget(self.count_label)
        
        btn_layout.addStretch()
        
        # 위로 이동
        self.up_btn = QPushButton("▲ 위로")
        self.up_btn.setMinimumHeight(36)
        self.up_btn.setMinimumWidth(80)
        self.up_btn.setToolTip("목록에서 위로 이동")
        self.up_btn.clicked.connect(self._move_up)
        btn_layout.addWidget(self.up_btn)
        
        # 아래로 이동
        self.down_btn = QPushButton("▼ 아래로")
        self.down_btn.setMinimumHeight(36)
        self.down_btn.setMinimumWidth(80)
        self.down_btn.setToolTip("목록에서 아래로 이동")
        self.down_btn.clicked.connect(self._move_down)
        btn_layout.addWidget(self.down_btn)
        
        # 삭제
        self.remove_btn = QPushButton("✕ 삭제")
        self.remove_btn.setMinimumHeight(36)
        self.remove_btn.setMinimumWidth(80)
        self.remove_btn.setToolTip("선택 항목 삭제")
        self.remove_btn.clicked.connect(self._remove_selected)
        btn_layout.addWidget(self.remove_btn)
        
        # 전체 삭제
        self.clear_btn = QPushButton("전체 삭제")
        self.clear_btn.setProperty("class", "secondary")
        self.clear_btn.clicked.connect(self._clear_all)
        btn_layout.addWidget(self.clear_btn)
        
        layout.addLayout(btn_layout)
    
    def _on_files_dropped(self, files: list[str]) -> None:
        """파일 드롭 처리"""
        for file_path in files:
            if file_path not in self._files:
                self._files.append(file_path)
                
                # 리스트에 추가
                item = QListWidgetItem()
                path = Path(file_path)
                item.setText(f"📄 {path.name}")
                item.setData(Qt.ItemDataRole.UserRole, file_path)
                item.setToolTip(file_path)
                self.list_widget.addItem(item)
        
        self._update_count()
        self.files_changed.emit(self._files)
    
    def _on_order_changed(self) -> None:
        """순서 변경 처리"""
        self._files = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item:
                file_path = item.data(Qt.ItemDataRole.UserRole)
                if file_path:
                    self._files.append(file_path)
        
        self.files_changed.emit(self._files)
    
    def _move_up(self) -> None:
        """선택된 항목 위로 이동"""
        current_row = self.list_widget.currentRow()
        if current_row > 0:
            item = self.list_widget.takeItem(current_row)
            self.list_widget.insertItem(current_row - 1, item)
            self.list_widget.setCurrentRow(current_row - 1)
            self._on_order_changed()
    
    def _move_down(self) -> None:
        """선택된 항목 아래로 이동"""
        current_row = self.list_widget.currentRow()
        if current_row < self.list_widget.count() - 1:
            item = self.list_widget.takeItem(current_row)
            self.list_widget.insertItem(current_row + 1, item)
            self.list_widget.setCurrentRow(current_row + 1)
            self._on_order_changed()
    
    def _remove_selected(self) -> None:
        """선택된 항목 삭제"""
        for item in self.list_widget.selectedItems():
            file_path = item.data(Qt.ItemDataRole.UserRole)
            if file_path in self._files:
                self._files.remove(file_path)
            self.list_widget.takeItem(self.list_widget.row(item))
        
        self._update_count()
        self.files_changed.emit(self._files)
    
    def _clear_all(self) -> None:
        """전체 삭제"""
        self._files.clear()
        self.list_widget.clear()
        self._update_count()
        self.files_changed.emit(self._files)
    
    def _update_count(self) -> None:
        """파일 개수 업데이트"""
        count = len(self._files)
        self.count_label.setText(f"{count}개 파일")
    
    def get_files(self) -> list[str]:
        """파일 목록 반환"""
        return self._files.copy()
    
    def set_files(self, files: list[str]) -> None:
        """파일 목록 설정"""
        self._clear_all()
        self._on_files_dropped(files)
    
    def add_file(self, file_path: str) -> None:
        """단일 파일 추가"""
        self._on_files_dropped([file_path])

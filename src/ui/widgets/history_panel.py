"""
History Panel Widget
작업 히스토리 UI 패널

Author: HWP Master
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QFrame
)
from PySide6.QtCore import Qt, Signal
from datetime import datetime

from ...utils.history_manager import get_history_manager, HistoryItem


class HistoryItemWidget(QFrame):
    """히스토리 항목 위젯"""
    
    replay_clicked = Signal(str)
    
    def __init__(self, item: HistoryItem, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._item = item
        self.setObjectName("historyItem")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)
        
        # 헤더
        header_layout = QHBoxLayout()
        
        type_label = QLabel(item.task_type)
        type_label.setStyleSheet("font-weight: bold; color: #8957e5;")
        header_layout.addWidget(type_label)
        
        header_layout.addStretch()
        
        # 시간
        try:
            dt = datetime.fromisoformat(item.timestamp)
            time_str = dt.strftime("%m/%d %H:%M")
        except Exception:
            time_str = item.timestamp[:10]
        
        time_label = QLabel(time_str)
        time_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        header_layout.addWidget(time_label)
        
        layout.addLayout(header_layout)
        
        # 설명
        desc_label = QLabel(item.description)
        desc_label.setStyleSheet("color: #e6edf3;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # 결과
        result_layout = QHBoxLayout()
        
        files_label = QLabel(f"📁 {item.file_count}개 파일")
        files_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        result_layout.addWidget(files_label)
        
        success_label = QLabel(f"✓ {item.success_count}")
        success_label.setStyleSheet("color: #3fb950; font-size: 11px;")
        result_layout.addWidget(success_label)
        
        if item.fail_count > 0:
            fail_label = QLabel(f"✗ {item.fail_count}")
            fail_label.setStyleSheet("color: #f85149; font-size: 11px;")
            result_layout.addWidget(fail_label)
        
        result_layout.addStretch()
        layout.addLayout(result_layout)
        
        self.setStyleSheet("""
            #historyItem {
                background: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
            #historyItem:hover {
                border-color: #8957e5;
            }
        """)


class HistoryPanel(QWidget):
    """히스토리 패널"""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._setup_ui()
        self._load_history()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 헤더
        header_layout = QHBoxLayout()
        
        title = QLabel("📋 최근 작업")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #e6edf3;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        clear_btn = QPushButton("지우기")
        clear_btn.setProperty("class", "secondary")
        clear_btn.setFixedSize(60, 28)
        clear_btn.clicked.connect(self._on_clear)
        header_layout.addWidget(clear_btn)
        
        layout.addLayout(header_layout)
        
        # 히스토리 목록
        self.list_widget = QListWidget()
        self.list_widget.setSpacing(8)
        self.list_widget.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
            }
            QListWidget::item {
                background: transparent;
                border: none;
            }
        """)
        layout.addWidget(self.list_widget)
    
    def _load_history(self) -> None:
        """히스토리 로드"""
        self.list_widget.clear()
        
        history = get_history_manager().get_recent(20)
        
        if not history:
            empty_label = QLabel("최근 작업 내역이 없습니다.")
            empty_label.setStyleSheet("color: #8b949e; padding: 20px;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            item = QListWidgetItem()
            item.setSizeHint(empty_label.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, empty_label)
            return
        
        for hist_item in history:
            widget = HistoryItemWidget(hist_item)
            
            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
    
    def _on_clear(self) -> None:
        """히스토리 지우기"""
        get_history_manager().clear()
        self._load_history()
    
    def refresh(self) -> None:
        """새로고침"""
        self._load_history()

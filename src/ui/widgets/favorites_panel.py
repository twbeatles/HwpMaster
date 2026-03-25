"""
Favorites Panel Widget
즐겨찾기 폴더 UI 패널

Author: HWP Master
"""

from typing import Optional
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QFileDialog
)
from PySide6.QtCore import Qt, Signal

from ...utils.settings import SettingsManager, get_settings_manager


class FavoritesPanel(QWidget):
    """즐겨찾기 폴더 패널"""
    
    folder_selected = Signal(str)
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        settings_manager: Optional[SettingsManager] = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings_manager or get_settings_manager()
        self._setup_ui()
        self._load_favorites()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 헤더
        header_layout = QHBoxLayout()
        
        title = QLabel("⭐ 즐겨찾기 폴더")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #e6edf3;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        add_btn = QPushButton("+")
        add_btn.setFixedSize(28, 28)
        add_btn.setToolTip("폴더 추가")
        add_btn.clicked.connect(self._on_add)
        header_layout.addWidget(add_btn)
        
        layout.addLayout(header_layout)
        
        # 폴더 목록
        self.list_widget = QListWidget()
        self.list_widget.setSpacing(4)
        self.list_widget.itemDoubleClicked.connect(self._on_item_clicked)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self.list_widget)
    
    def _load_favorites(self) -> None:
        """즐겨찾기 로드"""
        self.list_widget.clear()
        
        favorites = self._settings.get("favorite_folders", [])
        
        if not favorites:
            # 기본 폴더
            favorites = [str(Path.home() / "Documents")]
        
        for folder in favorites:
            if Path(folder).exists():
                self._add_folder_item(folder)
    
    def _add_folder_item(self, folder: str) -> None:
        """폴더 항목 추가"""
        item = QListWidgetItem()
        item.setText(f"📁 {Path(folder).name}")
        item.setData(Qt.ItemDataRole.UserRole, folder)
        item.setToolTip(folder)
        self.list_widget.addItem(item)
    
    def _on_add(self) -> None:
        """폴더 추가"""
        folder = QFileDialog.getExistingDirectory(self, "폴더 추가")
        if folder:
            favorites = self._settings.get("favorite_folders", [])
            
            if folder not in favorites:
                favorites.append(folder)
                self._settings.set("favorite_folders", favorites)
                self._add_folder_item(folder)
    
    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """폴더 클릭"""
        folder = item.data(Qt.ItemDataRole.UserRole)
        if folder:
            self.folder_selected.emit(folder)
    
    def _on_context_menu(self, pos) -> None:
        """우클릭 메뉴"""
        item = self.list_widget.itemAt(pos)
        if item:
            folder = item.data(Qt.ItemDataRole.UserRole)
            # 삭제 기능
            favorites = self._settings.get("favorite_folders", [])
            if folder in favorites:
                favorites.remove(folder)
                self._settings.set("favorite_folders", favorites)
            self.list_widget.takeItem(self.list_widget.row(item))
    
    def refresh(self) -> None:
        """새로고침"""
        self._load_favorites()

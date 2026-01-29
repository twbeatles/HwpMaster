"""
Toast Notification Widget
토스트 알림 시스템

Author: HWP Master
"""

from typing import Optional
from enum import Enum

from PySide6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QVBoxLayout,
    QGraphicsOpacityEffect, QPushButton
)
from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    QPoint, Signal
)
from PySide6.QtGui import QFont


class ToastType(Enum):
    """토스트 타입"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Toast(QWidget):
    """토스트 알림 위젯"""
    
    closed = Signal()
    
    ICONS = {
        ToastType.SUCCESS: "✓",
        ToastType.ERROR: "✕",
        ToastType.WARNING: "⚠",
        ToastType.INFO: "ℹ",
    }
    
    COLORS = {
        ToastType.SUCCESS: "#3fb950",
        ToastType.ERROR: "#f85149",
        ToastType.WARNING: "#d29922",
        ToastType.INFO: "#58a6ff",
    }
    
    def __init__(
        self,
        message: str,
        toast_type: ToastType = ToastType.INFO,
        duration: int = 3000,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("toast")
        self.setProperty("class", toast_type.value)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._toast_type = toast_type
        self._duration = duration
        
        self._setup_ui(message)
        self._setup_animation()
    
    def _setup_ui(self, message: str) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)
        
        # 아이콘
        icon_label = QLabel(self.ICONS.get(self._toast_type, "ℹ"))
        icon_label.setStyleSheet(f"""
            font-size: 20px;
            color: {self.COLORS.get(self._toast_type, '#58a6ff')};
            background: transparent;
        """)
        layout.addWidget(icon_label)
        
        # 메시지
        msg_label = QLabel(message)
        msg_label.setFont(QFont("Segoe UI", 12))
        msg_label.setStyleSheet("background: transparent; color: #e6edf3;")
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label, 1)
        
        # 닫기 버튼
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #8b949e;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #e6edf3;
            }
        """)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.hide_toast)
        layout.addWidget(close_btn)
        
        # 스타일
        color = self.COLORS.get(self._toast_type, '#58a6ff')
        self.setStyleSheet(f"""
            #toast {{
                background-color: #1c2128;
                border: 1px solid #30363d;
                border-left: 4px solid {color};
                border-radius: 12px;
                min-width: 320px;
                max-width: 450px;
            }}
        """)
        
        self.setMinimumWidth(320)
        self.adjustSize()
    
    def _setup_animation(self) -> None:
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(0)
        
        # 페이드 인
        self._fade_in = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_in.setDuration(200)
        self._fade_in.setStartValue(0)
        self._fade_in.setEndValue(1)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # 페이드 아웃
        self._fade_out = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_out.setDuration(200)
        self._fade_out.setStartValue(1)
        self._fade_out.setEndValue(0)
        self._fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_out.finished.connect(self._on_fade_out_finished)
        
        # 자동 숨김 타이머
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide_toast)
    
    def show_toast(self, parent_widget: Optional[QWidget] = None) -> None:
        """토스트 표시"""
        if parent_widget:
            # 부모 위젯 우측 상단에 배치
            parent_rect = parent_widget.geometry()
            x = parent_rect.right() - self.width() - 24
            y = parent_rect.top() + 80
            self.move(x, y)
        
        self.show()
        self._fade_in.start()
        
        if self._duration > 0:
            self._timer.start(self._duration)
    
    def hide_toast(self) -> None:
        """토스트 숨김"""
        self._timer.stop()
        self._fade_out.start()
    
    def _on_fade_out_finished(self) -> None:
        self.close()
        self.closed.emit()


class ToastManager:
    """토스트 관리자 (싱글톤)"""
    
    _instance: Optional["ToastManager"] = None
    
    def __new__(cls) -> "ToastManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._toasts: list[Toast] = []
            cls._instance._parent: Optional[QWidget] = None
        return cls._instance
    
    def set_parent(self, parent: QWidget) -> None:
        self._parent = parent
    
    def show_toast(
        self,
        message: str,
        toast_type: ToastType = ToastType.INFO,
        duration: int = 3000
    ) -> Toast:
        """토스트 표시"""
        toast = Toast(message, toast_type, duration)
        toast.closed.connect(lambda: self._remove_toast(toast))
        
        self._toasts.append(toast)
        self._reposition_toasts()
        toast.show_toast(self._parent)
        
        return toast
    
    def success(self, message: str, duration: int = 3000) -> Toast:
        return self.show_toast(message, ToastType.SUCCESS, duration)
    
    def error(self, message: str, duration: int = 4000) -> Toast:
        return self.show_toast(message, ToastType.ERROR, duration)
    
    def warning(self, message: str, duration: int = 3500) -> Toast:
        return self.show_toast(message, ToastType.WARNING, duration)
    
    def info(self, message: str, duration: int = 3000) -> Toast:
        return self.show_toast(message, ToastType.INFO, duration)
    
    def _remove_toast(self, toast: Toast) -> None:
        if toast in self._toasts:
            self._toasts.remove(toast)
            self._reposition_toasts()
    
    def _reposition_toasts(self) -> None:
        """토스트 위치 재정렬"""
        if not self._parent:
            return
        
        parent_rect = self._parent.geometry()
        y_offset = 80
        
        for toast in self._toasts:
            x = parent_rect.right() - toast.width() - 24
            y = parent_rect.top() + y_offset
            toast.move(x, y)
            y_offset += toast.height() + 12


# 편의 함수
def get_toast_manager() -> ToastManager:
    return ToastManager()

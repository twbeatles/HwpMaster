"""
Progress Card Widget
진행률 표시 카드 위젯

Author: HWP Master
"""

from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QProgressBar, QFrame, QPushButton
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont


class ProgressCard(QFrame):
    """진행률 표시 카드"""
    
    cancelled = Signal()
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setProperty("class", "card")
        self.setMinimumHeight(140)
        
        self.setStyleSheet("""
            ProgressCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #161b22, stop:1 #0d1117);
                border: 1px solid #30363d;
                border-radius: 16px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)
        
        # 상단: 제목 + 취소 버튼
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel("⏳ 작업 진행 중")
        self.title_label.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #e6edf3; background: transparent;")
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        self.cancel_btn = QPushButton("취소")
        self.cancel_btn.setProperty("class", "secondary")
        self.cancel_btn.setMinimumWidth(80)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.cancelled.emit)
        header_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(header_layout)
        
        # 상태 텍스트
        self.status_label = QLabel("준비 중...")
        self.status_label.setStyleSheet("color: #8b949e; background: transparent;")
        layout.addWidget(self.status_label)
        
        # 프로그레스 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setMinimumHeight(20)
        layout.addWidget(self.progress_bar)
        
        # 상세 정보
        detail_layout = QHBoxLayout()
        
        self.current_file_label = QLabel("")
        self.current_file_label.setStyleSheet("color: #484f58; font-size: 12px; background: transparent;")
        detail_layout.addWidget(self.current_file_label)
        
        detail_layout.addStretch()
        
        self.count_label = QLabel("")
        self.count_label.setStyleSheet("color: #8957e5; font-size: 12px; font-weight: 600; background: transparent;")
        detail_layout.addWidget(self.count_label)
        
        layout.addLayout(detail_layout)
        
        # 애니메이션
        self._animation: Optional[QPropertyAnimation] = None
    
    def set_title(self, title: str) -> None:
        """제목 설정"""
        self.title_label.setText(title)
    
    def set_status(self, status: str) -> None:
        """상태 텍스트 설정"""
        self.status_label.setText(status)
    
    def set_progress(self, value: int) -> None:
        """진행률 설정 (0-100)"""
        # 애니메이션으로 부드럽게 변경
        if self._animation:
            self._animation.stop()
        
        self._animation = QPropertyAnimation(self.progress_bar, b"value")
        self._animation.setDuration(200)
        self._animation.setStartValue(self.progress_bar.value())
        self._animation.setEndValue(value)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.start()
    
    def set_current_file(self, filename: str) -> None:
        """현재 처리 중인 파일 표시"""
        self.current_file_label.setText(f"📄 {filename}")
    
    def set_count(self, current: int, total: int) -> None:
        """진행 카운트 설정"""
        self.count_label.setText(f"{current} / {total}")
        
        # 진행률 자동 계산
        if total > 0:
            progress = int((current / total) * 100)
            self.set_progress(progress)
    
    def reset(self) -> None:
        """초기화"""
        self.title_label.setText("작업 진행 중")
        self.status_label.setText("준비 중...")
        self.progress_bar.setValue(0)
        self.current_file_label.setText("")
        self.count_label.setText("")
        self.cancel_btn.setEnabled(True)
    
    def set_completed(self, success_count: int, fail_count: int) -> None:
        """완료 상태로 변경"""
        self.set_progress(100)
        self.cancel_btn.setEnabled(False)
        
        if fail_count == 0:
            self.title_label.setText("✅ 작업 완료")
            self.status_label.setText(f"총 {success_count}개 파일 처리 완료")
            self.status_label.setStyleSheet("color: #3fb950; background: transparent;")
        else:
            self.title_label.setText("⚠️ 작업 완료 (일부 실패)")
            self.status_label.setText(f"성공: {success_count}개, 실패: {fail_count}개")
            self.status_label.setStyleSheet("color: #d29922; background: transparent;")
    
    def set_error(self, message: str) -> None:
        """에러 상태로 변경"""
        self.title_label.setText("❌ 오류 발생")
        self.status_label.setText(message)
        self.status_label.setStyleSheet("color: #f85149; background: transparent;")
        self.cancel_btn.setText("닫기")


class ToastNotification(QFrame):
    """토스트 알림"""
    
    closed = Signal()
    
    def __init__(
        self,
        message: str,
        toast_type: str = "info",  # info, success, warning, error
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("toast")
        self.setProperty("class", toast_type)
        self.setFixedHeight(50)
        self.setMinimumWidth(300)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        
        # 아이콘
        icons = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
        }
        icon_label = QLabel(icons.get(toast_type, "ℹ️"))
        layout.addWidget(icon_label)
        
        # 메시지
        msg_label = QLabel(message)
        layout.addWidget(msg_label, 1)
        
        # 닫기 버튼
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("background: transparent; border: none;")
        close_btn.clicked.connect(self._close)
        layout.addWidget(close_btn)
        
        # 페이드 인 애니메이션
        self.setWindowOpacity(0)
        self._fade_in()
    
    def _fade_in(self) -> None:
        """페이드 인"""
        self._animation = QPropertyAnimation(self, b"windowOpacity")
        self._animation.setDuration(200)
        self._animation.setStartValue(0)
        self._animation.setEndValue(1)
        self._animation.start()
    
    def _close(self) -> None:
        """닫기"""
        animation = QPropertyAnimation(self, b"windowOpacity")
        animation.setDuration(200)
        animation.setStartValue(1)
        animation.setEndValue(0)
        animation.finished.connect(self._on_close_finished)
        animation.start()
        self._close_animation = animation  # 참조 유지
    
    def _on_close_finished(self) -> None:
        self.closed.emit()
        self.deleteLater()

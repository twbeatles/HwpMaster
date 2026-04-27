"""
Home Page
홈 대시보드 페이지

Author: HWP Master
"""
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGridLayout, QFrame, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from ...utils.history_manager import HistoryManager
from ...utils.settings import SettingsManager
from ..widgets.feature_card import FeatureCard
from ..widgets.favorites_panel import FavoritesPanel
from ..widgets.history_panel import HistoryPanel
from ..widgets.page_header import SectionHeader


class HomePage(QWidget):
    """홈 대시보드 페이지"""
    
    card_clicked = Signal(int)
    
    # 카테고리별 기능 목록 (이모지, 제목, 설명, 페이지 인덱스)
    SECTIONS: list[tuple[str, list[tuple[str, str, str, int]]]] = [
        ("기본", [
            ("✍", "문서 편집", "HWP/HWPX 문서를 열고 편집·저장", 18),
            ("🔄", "스마트 변환", "HWP → PDF, TXT, HWPX, JPG 일괄 변환", 1),
            ("📎", "병합/분할", "여러 파일 병합 및 페이지별 분할", 2),
            ("📝", "데이터 주입", "Excel 데이터를 HWP 템플릿에 자동 입력", 3),
            ("🧹", "메타정보 정리", "작성자, 메모 등 민감정보 일괄 삭제", 4),
        ]),
        ("고급", [
            ("📦", "템플릿 스토어", "내장/사용자 양식 관리 및 빠른 생성", 5),
            ("🎬", "매크로 레코더", "반복 작업 녹화 및 프리셋 매크로 실행", 6),
            ("🔤", "정규식 치환", "패턴 기반 민감정보 마스킹 처리", 7),
            ("🧰", "액션 콘솔", "Run/Execute 액션을 JSON으로 실행하고 템플릿으로 재사용", 17),
        ]),
        ("분석", [
            ("👮", "서식 도우미", "폰트·줄간격·자간을 표준으로 통일", 8),
            ("🩺", "표 도우미", "표 테두리·여백·배경색 일괄 변경", 9),
            ("📊", "문서 비교", "두 문서의 차이점을 HTML 리포트로 생성", 10),
            ("📑", "자동 목차", "글자 크기/굵기 분석으로 목차 자동 생성", 11),
        ]),
        ("생산성", [
            ("💧", "워터마크", "텍스트/이미지 워터마크 일괄 삽입", 12),
            ("📄", "헤더/푸터", "머리말·꼬리말·쪽 번호 일괄 적용", 13),
            ("🔖", "북마크", "북마크 추출 및 일괄 삭제", 14),
            ("🔗", "링크 검사", "하이퍼링크 유효성 검사 및 엑셀 내보내기", 15),
            ("🖼️", "이미지 추출", "문서 내 이미지 원본 화질 추출", 16),
        ]),
    ]
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        settings_manager: Optional[SettingsManager] = None,
        history_manager: Optional[HistoryManager] = None,
    ) -> None:
        super().__init__(parent)
        self._settings_manager = settings_manager
        self._history_manager = history_manager
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 0, 40, 40)
        layout.setSpacing(0)
        
        # ── 히어로 배너 ──
        hero = QFrame()
        hero.setObjectName("heroBanner")
        hero.setStyleSheet("""
            #heroBanner {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(139, 92, 246, 0.15),
                    stop:0.5 rgba(59, 130, 246, 0.10),
                    stop:1 rgba(139, 92, 246, 0.05));
                border: 1px solid rgba(51, 58, 69, 0.5);
                border-radius: 24px;
            }
            #heroBanner * {
                background: transparent;
                border: none;
            }
        """)
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(48, 48, 48, 48)
        hero_layout.setSpacing(12)

        hero_icon = QLabel("📄")
        hero_icon.setStyleSheet("font-size: 42px;")
        hero_layout.addWidget(hero_icon)

        hero_title = QLabel("HWP Master")
        hero_title.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        hero_title.setStyleSheet("color: #ffffff;")
        hero_layout.addWidget(hero_title)

        hero_subtitle = QLabel("HWP 업무 자동화를 위한 올인원 도구")
        hero_subtitle.setFont(QFont("Segoe UI", 16))
        hero_subtitle.setStyleSheet("color: #9ca3af;")
        hero_layout.addWidget(hero_subtitle)

        layout.addSpacing(32)
        layout.addWidget(hero)
        layout.addSpacing(32)

        panel_row = QHBoxLayout()
        panel_row.setSpacing(16)

        self.history_panel = HistoryPanel(history_manager=self._history_manager)
        self.favorites_panel = FavoritesPanel(settings_manager=self._settings_manager)
        panel_row.addWidget(self.history_panel, 2)
        panel_row.addWidget(self.favorites_panel, 1)

        layout.addLayout(panel_row)
        layout.addSpacing(32)
        
        # ── 카테고리별 카드 그리드 ──
        for section_name, cards in self.SECTIONS:
            header = SectionHeader(section_name)
            layout.addWidget(header)
            
            grid = QGridLayout()
            grid.setSpacing(16)
            grid.setContentsMargins(0, 0, 0, 16)
            
            for col_idx, (emoji, title, desc, page_idx) in enumerate(cards):
                card = FeatureCard(
                    title=title,
                    description=desc,
                    icon_emoji=emoji,
                )
                card.clicked.connect(
                    lambda idx=page_idx: self.card_clicked.emit(idx)
                )
                row = col_idx // 3
                col = col_idx % 3
                grid.addWidget(card, row, col)
            
            # 빈 열 채우기 (3열 그리드 유지)
            remaining = len(cards) % 3
            if remaining != 0:
                for i in range(remaining, 3):
                    spacer = QWidget()
                    spacer.setSizePolicy(
                        QSizePolicy.Policy.Expanding,
                        QSizePolicy.Policy.Fixed
                    )
                    grid.addWidget(spacer, (len(cards) - 1) // 3, i)
            
            layout.addLayout(grid)
        
        layout.addStretch()
        
        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

    def refresh_panels(self) -> None:
        self.history_panel.refresh()
        self.favorites_panel.refresh()

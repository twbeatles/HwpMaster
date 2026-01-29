"""
HWP Master - HWP 업무 자동화 도구
프로그램 진입점

Author: HWP Master
Version: 1.0.0
"""

import sys
import os
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QFile, QTextStream
from PySide6.QtGui import QFont, QFontDatabase


def load_stylesheet(app: QApplication) -> None:
    """QSS 스타일시트 로드"""
    # 스타일시트 경로 결정
    if getattr(sys, 'frozen', False):
        # PyInstaller 번들
        base_path = Path(sys._MEIPASS)
    else:
        # 개발 환경
        base_path = Path(__file__).parent
    
    style_path = base_path / "assets" / "styles" / "style.qss"
    
    if style_path.exists():
        file = QFile(str(style_path))
        if file.open(QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text):
            stream = QTextStream(file)
            stylesheet = stream.readAll()
            app.setStyleSheet(stylesheet)
            file.close()
    else:
        # 기본 스타일 (스타일시트 파일 없을 경우)
        app.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a2e;
            }
            QWidget {
                background-color: #1a1a2e;
                color: #e8e8e8;
                font-family: "Segoe UI", "Malgun Gothic", sans-serif;
            }
        """)


def setup_fonts() -> None:
    """폰트 설정"""
    # 시스템 기본 폰트 사용 (Segoe UI, Malgun Gothic)
    # 커스텀 폰트가 필요한 경우 여기서 로드
    pass


def main() -> int:
    """메인 함수"""
    # High DPI 지원
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # 애플리케이션 생성
    app = QApplication(sys.argv)
    app.setApplicationName("HWP Master")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("HWP Master")
    
    # 기본 폰트 설정
    default_font = QFont("Segoe UI", 10)
    default_font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(default_font)
    
    # 스타일시트 로드
    load_stylesheet(app)
    
    # 폰트 설정
    setup_fonts()
    
    # 메인 윈도우 생성 및 표시
    from src.ui.main_window import MainWindow
    
    window = MainWindow()
    window.show()
    
    # 로거 설정
    from src.utils.logger import setup_logger
    logger = setup_logger()
    logger.info("HWP Master 시작")
    
    # 애플리케이션 실행
    exit_code = app.exec()
    
    logger.info("HWP Master 종료")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

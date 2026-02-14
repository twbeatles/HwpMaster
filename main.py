"""
HWP Master - HWP 업무 자동화 도구
프로그램 진입점

Author: HWP Master
"""

import sys
import os
import logging
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QFile, QTextStream
from PySide6.QtGui import QFont, QFontDatabase


def load_stylesheet(app: QApplication) -> None:
    """QSS 스타일시트 로드 (테마 프리셋 지원)"""
    try:
        from src.utils.settings import get_settings_manager
        from src.utils.qss_renderer import build_stylesheet

        settings = get_settings_manager()
        preset = settings.get("theme_preset", "Dark (기본)")
        app.setStyleSheet(build_stylesheet(preset))
        return
    except Exception as e:
        # fallback to bundled style.qss
        logging.getLogger(__name__).warning(f"테마 QSS 적용 실패, 기본 QSS로 fallback: {e}")

    if getattr(sys, "frozen", False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent

    style_path = base_path / "assets" / "styles" / "style.qss"

    if style_path.exists():
        file = QFile(str(style_path))
        if file.open(QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text):
            stream = QTextStream(file)
            stylesheet = stream.readAll()
            app.setStyleSheet(stylesheet)
            file.close()
        return

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
    from src.utils.version import APP_NAME, APP_VERSION

    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_NAME)
    
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

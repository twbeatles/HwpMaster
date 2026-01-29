"""
Logger Module
로깅 설정

Author: HWP Master
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


def setup_logger(
    name: str = "hwp_master",
    level: int = logging.INFO,
    log_dir: Optional[str] = None,
    console_output: bool = True,
    file_output: bool = True
) -> logging.Logger:
    """
    로거 설정
    
    Args:
        name: 로거 이름
        level: 로그 레벨
        log_dir: 로그 파일 디렉토리
        console_output: 콘솔 출력 여부
        file_output: 파일 출력 여부
    
    Returns:
        설정된 Logger 객체
    """
    logger = logging.getLogger(name)
    
    # 이미 핸들러가 있으면 반환
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # 포맷터
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # 콘솔 핸들러
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # 파일 핸들러
    if file_output:
        if log_dir is None:
            log_dir = str(Path.home() / ".hwp_master" / "logs")
        
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # 날짜별 로그 파일
        log_file = log_path / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
        
        file_handler = logging.FileHandler(
            str(log_file),
            encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "hwp_master") -> logging.Logger:
    """기존 로거 가져오기"""
    return logging.getLogger(name)


class LogCapture:
    """
    로그 메시지 캡처 (UI 표시용)
    
    Usage:
        with LogCapture() as capture:
            logger.info("test")
        messages = capture.messages
    """
    
    def __init__(self, logger_name: str = "hwp_master"):
        self._logger = logging.getLogger(logger_name)
        self._handler: Optional[logging.Handler] = None
        self.messages: list[str] = []
    
    def __enter__(self):
        class ListHandler(logging.Handler):
            def __init__(self, message_list: list):
                super().__init__()
                self.message_list = message_list
            
            def emit(self, record):
                self.message_list.append(self.format(record))
        
        self._handler = ListHandler(self.messages)
        self._handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        self._logger.addHandler(self._handler)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._handler:
            self._logger.removeHandler(self._handler)
        return False

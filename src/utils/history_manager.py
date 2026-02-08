"""
History Manager Module
작업 히스토리 관리

Author: HWP Master
"""

import json
from pathlib import Path
from typing import Optional, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum


class TaskType(Enum):
    """작업 유형"""
    CONVERT = "변환"
    MERGE = "병합"
    SPLIT = "분할"
    DATA_INJECT = "데이터 주입"
    METADATA = "메타정보 정리"
    WATERMARK = "워터마크"
    HEADER_FOOTER = "헤더/푸터"
    BOOKMARK = "북마크"
    HYPERLINK = "링크 검사"
    IMAGE_EXTRACT = "이미지 추출"
    REGEX = "정규식 치환"
    STYLE = "서식 통일"
    TABLE = "표 수정"
    DIFF = "문서 비교"
    TOC = "목차 생성"


@dataclass
class HistoryItem:
    """히스토리 항목"""
    id: str
    task_type: str
    description: str
    file_count: int
    success_count: int
    fail_count: int
    timestamp: str
    files: list[str] = field(default_factory=list)
    options: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.files is None:
            self.files = []
        if self.options is None:
            self.options = {}


class HistoryManager:
    """히스토리 관리자"""
    
    MAX_HISTORY = 100
    
    def __init__(self, config_dir: Optional[str] = None) -> None:
        if config_dir:
            self._config_dir = Path(config_dir)
        else:
            self._config_dir = Path.home() / ".hwp_master"
        
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._history_file = self._config_dir / "history.json"
        self._history: list[HistoryItem] = []
        self.load()
    
    def load(self) -> None:
        """히스토리 불러오기"""
        if self._history_file.exists():
            try:
                with open(self._history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._history = [HistoryItem(**item) for item in data]
            except Exception:
                self._history = []
    
    def save(self) -> None:
        """히스토리 저장"""
        try:
            with open(self._history_file, "w", encoding="utf-8") as f:
                data = [asdict(item) for item in self._history]
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    
    def add(
        self,
        task_type: TaskType,
        description: str,
        files: list[str],
        success_count: int,
        fail_count: int,
        options: Optional[dict[str, Any]] = None
    ) -> HistoryItem:
        """히스토리 추가"""
        item = HistoryItem(
            id=datetime.now().strftime("%Y%m%d%H%M%S%f"),
            task_type=task_type.value,
            description=description,
            file_count=len(files),
            success_count=success_count,
            fail_count=fail_count,
            timestamp=datetime.now().isoformat(),
            files=files[:10],  # 최대 10개 파일만 저장
            options=options or {}
        )
        
        self._history.insert(0, item)
        
        # 최대 개수 유지
        if len(self._history) > self.MAX_HISTORY:
            self._history = self._history[:self.MAX_HISTORY]
        
        self.save()
        return item
    
    def get_all(self) -> list[HistoryItem]:
        """전체 히스토리 반환"""
        return self._history.copy()
    
    def get_recent(self, count: int = 10) -> list[HistoryItem]:
        """최근 히스토리 반환"""
        return self._history[:count]
    
    def get_by_type(self, task_type: TaskType) -> list[HistoryItem]:
        """작업 유형별 히스토리"""
        return [h for h in self._history if h.task_type == task_type.value]
    
    def delete(self, item_id: str) -> bool:
        """히스토리 삭제"""
        for i, item in enumerate(self._history):
            if item.id == item_id:
                del self._history[i]
                self.save()
                return True
        return False
    
    def clear(self) -> None:
        """전체 히스토리 삭제"""
        self._history.clear()
        self.save()


# 싱글톤
_history_manager: Optional[HistoryManager] = None


def get_history_manager() -> HistoryManager:
    """히스토리 관리자 인스턴스 반환"""
    global _history_manager
    if _history_manager is None:
        _history_manager = HistoryManager()
    return _history_manager

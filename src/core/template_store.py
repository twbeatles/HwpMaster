"""
Template Store Module
스마트 템플릿 스토어 - 공문서 양식 관리

Author: HWP Master
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Optional, Any, TypedDict
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum


class TemplateCategory(Enum):
    """템플릿 카테고리"""
    LEAVE = "휴가"
    EXPENSE = "지출"
    MEETING = "회의"
    REPORT = "보고서"
    CONTRACT = "계약"
    LETTER = "공문"
    OTHER = "기타"


@dataclass
class TemplateInfo:
    """템플릿 정보"""
    id: str
    name: str
    description: str
    category: str
    file_path: str
    thumbnail_path: Optional[str] = None
    is_builtin: bool = False
    is_favorite: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    used_count: int = 0
    fields: list[str] = field(default_factory=list)  # 누름틀 필드 목록
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TemplateInfo":
        return cls(**data)


class BuiltinTemplateSpec(TypedDict):
    """내장 템플릿 스펙"""
    id: str
    name: str
    description: str
    category: str
    fields: list[str]


class TemplateStore:
    """
    템플릿 스토어 관리 클래스
    내장 템플릿 및 사용자 템플릿 관리
    """
    
    # 내장 템플릿 정의
    BUILTIN_TEMPLATES: list[BuiltinTemplateSpec] = [
        {
            "id": "leave_annual",
            "name": "연차휴가 신청서",
            "description": "연차휴가 사용 신청을 위한 표준 양식",
            "category": "휴가",
            "fields": ["성명", "부서", "직급", "휴가기간", "휴가일수", "사유", "날짜"]
        },
        {
            "id": "leave_sick",
            "name": "병가 신청서",
            "description": "질병으로 인한 휴가 신청 양식",
            "category": "휴가",
            "fields": ["성명", "부서", "휴가기간", "병명", "첨부서류", "날짜"]
        },
        {
            "id": "expense_general",
            "name": "지출결의서",
            "description": "일반 경비 지출 결의 양식",
            "category": "지출",
            "fields": ["결재일", "부서", "품의자", "지출항목", "금액", "내역", "비고"]
        },
        {
            "id": "expense_travel",
            "name": "출장비 정산서",
            "description": "출장 경비 정산 양식",
            "category": "지출",
            "fields": ["성명", "부서", "출장기간", "출장지", "교통비", "숙박비", "식비", "합계"]
        },
        {
            "id": "meeting_minutes",
            "name": "회의록",
            "description": "회의 내용 기록 양식",
            "category": "회의",
            "fields": ["회의명", "일시", "장소", "참석자", "안건", "내용", "결정사항", "작성자"]
        },
        {
            "id": "report_weekly",
            "name": "주간업무보고",
            "description": "주간 업무 현황 보고 양식",
            "category": "보고서",
            "fields": ["보고기간", "부서", "성명", "금주실적", "차주계획", "특이사항"]
        },
        {
            "id": "report_project",
            "name": "프로젝트 완료보고서",
            "description": "프로젝트 완료 후 최종 보고 양식",
            "category": "보고서",
            "fields": ["프로젝트명", "기간", "담당자", "목표", "결과", "성과", "향후계획"]
        },
        {
            "id": "letter_official",
            "name": "대외공문",
            "description": "대외 발송용 공식 문서 양식",
            "category": "공문",
            "fields": ["문서번호", "수신", "참조", "제목", "본문", "발신일", "발신자"]
        },
    ]
    
    def __init__(self, base_dir: Optional[str] = None) -> None:
        """
        Args:
            base_dir: 기본 디렉토리 (None이면 사용자 문서 폴더)
        """
        self._logger = logging.getLogger(__name__)
        
        if base_dir:
            self._base_dir = Path(base_dir)
        else:
            self._base_dir = Path.home() / ".hwp_master" / "templates"
        
        self._templates_dir = self._base_dir / "files"
        self._user_templates_dir = self._base_dir / "user"
        self._metadata_file = self._base_dir / "templates.json"
        
        self._templates: dict[str, TemplateInfo] = {}
        
        self._init_directories()
        self._load_metadata()
        self._init_builtin_templates()
    
    def _init_directories(self) -> None:
        """디렉토리 초기화"""
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._templates_dir.mkdir(exist_ok=True)
        self._user_templates_dir.mkdir(exist_ok=True)
    
    def _load_metadata(self) -> None:
        """메타데이터 로드"""
        if self._metadata_file.exists():
            try:
                with open(self._metadata_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.get("templates", []):
                        template = TemplateInfo.from_dict(item)
                        self._templates[template.id] = template
            except Exception as e:
                self._logger.warning(f"템플릿 메타데이터 로드 실패: {e}")
    
    def _save_metadata(self) -> None:
        """메타데이터 저장"""
        data = {
            "version": "1.0",
            "templates": [t.to_dict() for t in self._templates.values()]
        }
        with open(self._metadata_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _init_builtin_templates(self) -> None:
        """내장 템플릿 초기화"""
        for builtin in self.BUILTIN_TEMPLATES:
            template_id = builtin["id"]
            if template_id not in self._templates:
                # 실제 HWP 파일은 없지만 메타데이터만 등록
                self._templates[template_id] = TemplateInfo(
                    id=template_id,
                    name=builtin["name"],
                    description=builtin["description"],
                    category=builtin["category"],
                    file_path="",  # 실제 파일 경로는 나중에 설정
                    is_builtin=True,
                    fields=builtin.get("fields", [])
                )
        self._save_metadata()
    
    def get_all_templates(self) -> list[TemplateInfo]:
        """모든 템플릿 목록 반환"""
        return list(self._templates.values())
    
    def get_templates_by_category(self, category: str) -> list[TemplateInfo]:
        """카테고리별 템플릿 목록"""
        return [t for t in self._templates.values() if t.category == category]
    
    def get_favorite_templates(self) -> list[TemplateInfo]:
        """즐겨찾기 템플릿 목록"""
        return [t for t in self._templates.values() if t.is_favorite]
    
    def get_recent_templates(self, limit: int = 5) -> list[TemplateInfo]:
        """최근 사용 템플릿"""
        sorted_templates = sorted(
            self._templates.values(),
            key=lambda t: t.used_count,
            reverse=True
        )
        return sorted_templates[:limit]
    
    def get_template(self, template_id: str) -> Optional[TemplateInfo]:
        """템플릿 정보 조회"""
        return self._templates.get(template_id)
    
    def add_user_template(
        self,
        name: str,
        file_path: str,
        description: str = "",
        category: str = "기타"
    ) -> TemplateInfo:
        """
        사용자 템플릿 추가
        
        Args:
            name: 템플릿 이름
            file_path: HWP 파일 경로
            description: 설명
            category: 카테고리
        
        Returns:
            생성된 TemplateInfo
        """
        # 고유 ID 생성
        template_id = f"user_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 파일 복사
        source = Path(file_path)
        dest = self._user_templates_dir / f"{template_id}{source.suffix}"
        shutil.copy2(source, dest)
        
        # 템플릿 정보 생성
        template = TemplateInfo(
            id=template_id,
            name=name,
            description=description,
            category=category,
            file_path=str(dest),
            is_builtin=False
        )
        
        self._templates[template_id] = template
        self._save_metadata()
        
        return template
    
    def remove_template(self, template_id: str) -> bool:
        """
        템플릿 삭제 (사용자 템플릿만)
        
        Args:
            template_id: 템플릿 ID
        
        Returns:
            성공 여부
        """
        template = self._templates.get(template_id)
        if not template or template.is_builtin:
            return False
        
        # 파일 삭제
        if template.file_path:
            file_path = Path(template.file_path)
            if file_path.exists():
                file_path.unlink()
        
        # 메타데이터에서 제거
        del self._templates[template_id]
        self._save_metadata()
        
        return True
    
    def toggle_favorite(self, template_id: str) -> bool:
        """즐겨찾기 토글"""
        template = self._templates.get(template_id)
        if template:
            template.is_favorite = not template.is_favorite
            self._save_metadata()
            return template.is_favorite
        return False
    
    def increment_usage(self, template_id: str) -> None:
        """사용 횟수 증가"""
        template = self._templates.get(template_id)
        if template:
            template.used_count += 1
            self._save_metadata()
    
    def use_template(self, template_id: str, output_path: str) -> Optional[str]:
        """
        템플릿 사용 (파일 복사)
        
        Args:
            template_id: 템플릿 ID
            output_path: 출력 경로
        
        Returns:
            생성된 파일 경로 또는 None
        
        Raises:
            ValueError: 내장 템플릿 파일이 등록되지 않은 경우
        """
        template = self._templates.get(template_id)
        if not template:
            return None
        
        if not template.file_path:
            if template.is_builtin:
                raise ValueError(
                    f"내장 템플릿 '{template.name}'의 HWP 파일이 없습니다. "
                    f"'{template.name}' 템플릿 사용을 위해 먼저 HWP 파일을 등록해주세요."
                )
            return None
        
        source = Path(template.file_path)
        if not source.exists():
            self._logger.warning(f"템플릿 파일이 존재하지 않습니다: {template.file_path}")
            return None
        
        dest = Path(output_path)
        shutil.copy2(source, dest)
        
        self.increment_usage(template_id)
        
        return str(dest)
    
    def create_from_template(
        self,
        template_id: str,
        data: dict[str, str],
        output_path: str
    ) -> Optional[str]:
        """
        템플릿에서 문서 생성 (데이터 주입)
        
        Args:
            template_id: 템플릿 ID
            data: 필드-값 매핑
            output_path: 출력 경로
        
        Returns:
            생성된 파일 경로 또는 None
        """
        template = self._templates.get(template_id)
        if not template or not template.file_path:
            return None
        
        try:
            from .hwp_handler import HwpHandler
            
            with HwpHandler() as handler:
                result = handler.inject_data(template.file_path, data, output_path)
                
                if result.success:
                    self.increment_usage(template_id)
                    return result.output_path
                    
        except Exception as e:
            self._logger.warning(f"템플릿 생성 중 오류 발생: {e}")
        
        return None
    
    def search_templates(self, query: str) -> list[TemplateInfo]:
        """템플릿 검색"""
        query_lower = query.lower()
        return [
            t for t in self._templates.values()
            if query_lower in t.name.lower() 
            or query_lower in t.description.lower()
            or query_lower in t.category.lower()
        ]
    
    def get_categories(self) -> list[str]:
        """모든 카테고리 목록"""
        categories = set(t.category for t in self._templates.values())
        return sorted(categories)
    
    def register_builtin_template_file(
        self,
        template_id: str,
        file_path: str
    ) -> bool:
        """
        내장 템플릿에 HWP 파일 등록
        
        사용자가 직접 HWP 파일을 선택하여 내장 템플릿에 연결할 수 있습니다.
        
        Args:
            template_id: 내장 템플릿 ID (예: "leave_annual")
            file_path: HWP 파일 경로
        
        Returns:
            등록 성공 여부
        """
        template = self._templates.get(template_id)
        if not template or not template.is_builtin:
            self._logger.warning(f"내장 템플릿이 아니거나 존재하지 않는 ID: {template_id}")
            return False
        
        source = Path(file_path)
        if not source.exists():
            self._logger.warning(f"파일이 존재하지 않습니다: {file_path}")
            return False
        
        # 파일을 템플릿 디렉토리로 복사
        dest = self._templates_dir / f"{template_id}{source.suffix}"
        shutil.copy2(source, dest)
        
        # 템플릿 정보 업데이트
        template.file_path = str(dest)
        self._save_metadata()
        
        self._logger.info(f"내장 템플릿 '{template.name}'에 파일이 등록되었습니다: {dest}")
        return True
    
    def get_unregistered_templates(self) -> list[TemplateInfo]:
        """
        파일이 등록되지 않은 내장 템플릿 목록 반환
        
        Returns:
            파일이 없는 내장 템플릿 목록
        """
        return [
            t for t in self._templates.values()
            if t.is_builtin and not t.file_path
        ]
    
    def get_registered_templates(self) -> list[TemplateInfo]:
        """
        파일이 등록된 템플릿 목록 반환 (사용 가능한 템플릿)
        
        Returns:
            파일이 있는 템플릿 목록
        """
        return [
            t for t in self._templates.values()
            if t.file_path and Path(t.file_path).exists()
        ]
    
    def is_template_ready(self, template_id: str) -> bool:
        """
        템플릿이 사용 가능한 상태인지 확인
        
        Args:
            template_id: 템플릿 ID
        
        Returns:
            사용 가능 여부
        """
        template = self._templates.get(template_id)
        if not template:
            return False
        
        if not template.file_path:
            return False
        
        return Path(template.file_path).exists()


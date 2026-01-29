"""
Regex Replacer Module
정규식 기반 텍스트 치환

Author: HWP Master
"""

import re
import logging
from typing import Optional, Any, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum


class MaskingPreset(Enum):
    """마스킹 프리셋"""
    RESIDENT_ID = "주민등록번호"
    PHONE = "전화번호"
    EMAIL = "이메일"
    CARD_NUMBER = "카드번호"
    ACCOUNT_NUMBER = "계좌번호"
    NAME = "이름"
    ADDRESS = "주소"


@dataclass
class ReplacementRule:
    """치환 규칙"""
    name: str
    pattern: str
    replacement: str
    description: str = ""
    is_regex: bool = True
    case_sensitive: bool = False
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "ReplacementRule":
        return cls(**data)


@dataclass
class ReplacementResult:
    """치환 결과"""
    success: bool
    original_count: int = 0
    replaced_count: int = 0
    preview: list[tuple[str, str]] = field(default_factory=list)  # (before, after)
    error_message: Optional[str] = None


class RegexReplacer:
    """
    정규식 기반 텍스트 치환기
    민감정보 마스킹 등 패턴 기반 치환
    """
    
    # 내장 프리셋 정의
    PRESETS: dict[str, ReplacementRule] = {
        "resident_id": ReplacementRule(
            name="주민등록번호 마스킹",
            pattern=r"(\d{6})-(\d{7})",
            replacement=r"\1-*******",
            description="주민등록번호 뒷자리 7자리를 *로 마스킹"
        ),
        "resident_id_full": ReplacementRule(
            name="주민등록번호 전체 마스킹",
            pattern=r"\d{6}-\d{7}",
            replacement="******-*******",
            description="주민등록번호 전체를 *로 마스킹"
        ),
        "phone_mobile": ReplacementRule(
            name="휴대폰번호 마스킹",
            pattern=r"(01[0-9])-?(\d{3,4})-?(\d{4})",
            replacement=r"\1-****-\3",
            description="휴대폰번호 중간 4자리를 *로 마스킹"
        ),
        "phone_landline": ReplacementRule(
            name="전화번호 마스킹",
            pattern=r"(0\d{1,2})-?(\d{3,4})-?(\d{4})",
            replacement=r"\1-****-\3",
            description="전화번호 중간 자리를 *로 마스킹"
        ),
        "email": ReplacementRule(
            name="이메일 마스킹",
            pattern=r"([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
            replacement=r"***@\2",
            description="이메일 아이디 부분을 *로 마스킹"
        ),
        "email_full": ReplacementRule(
            name="이메일 전체 마스킹",
            pattern=r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            replacement="***@***.***",
            description="이메일 전체를 마스킹"
        ),
        "card_number": ReplacementRule(
            name="카드번호 마스킹",
            pattern=r"(\d{4})-?(\d{4})-?(\d{4})-?(\d{4})",
            replacement=r"\1-****-****-\4",
            description="카드번호 중간 8자리를 *로 마스킹"
        ),
        "account_number": ReplacementRule(
            name="계좌번호 마스킹",
            pattern=r"(\d{3,4})-?(\d{2,6})-?(\d{2,6})",
            replacement=r"\1-******-**",
            description="계좌번호 일부를 *로 마스킹"
        ),
        "korean_name": ReplacementRule(
            name="한글 이름 마스킹 (3자)",
            pattern=r"([가-힣])([가-힣])([가-힣])",
            replacement=r"\1*\3",
            description="3자 한글 이름의 중간 글자를 *로 마스킹"
        ),
        "korean_name_2": ReplacementRule(
            name="한글 이름 마스킹 (2자)",
            pattern=r"([가-힣])([가-힣])",
            replacement=r"\1*",
            description="2자 한글 이름의 마지막 글자를 *로 마스킹"
        ),
        "ip_address": ReplacementRule(
            name="IP 주소 마스킹",
            pattern=r"(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})",
            replacement=r"\1.\2.*.*",
            description="IP 주소의 마지막 두 옥텟을 *로 마스킹"
        ),
    }
    
    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        self._custom_rules: list[ReplacementRule] = []
    
    def get_presets(self) -> list[ReplacementRule]:
        """프리셋 목록 반환"""
        return list(self.PRESETS.values())
    
    def get_preset(self, preset_id: str) -> Optional[ReplacementRule]:
        """프리셋 조회"""
        return self.PRESETS.get(preset_id)
    
    def add_custom_rule(self, rule: ReplacementRule) -> None:
        """커스텀 규칙 추가"""
        self._custom_rules.append(rule)
    
    def get_custom_rules(self) -> list[ReplacementRule]:
        """커스텀 규칙 목록"""
        return self._custom_rules.copy()
    
    def validate_pattern(self, pattern: str) -> tuple[bool, str]:
        """
        정규식 패턴 유효성 검사
        
        Returns:
            (유효 여부, 오류 메시지)
        """
        try:
            re.compile(pattern)
            return True, ""
        except re.error as e:
            return False, str(e)
    
    def preview_replacement(
        self,
        text: str,
        rule: ReplacementRule,
        max_previews: int = 5
    ) -> ReplacementResult:
        """
        치환 미리보기
        
        Args:
            text: 원본 텍스트
            rule: 치환 규칙
            max_previews: 최대 미리보기 개수
        
        Returns:
            ReplacementResult
        """
        try:
            flags = 0 if rule.case_sensitive else re.IGNORECASE
            
            if rule.is_regex:
                pattern = re.compile(rule.pattern, flags)
            else:
                pattern = re.compile(re.escape(rule.pattern), flags)
            
            matches = pattern.findall(text)
            original_count = len(matches)
            
            # 미리보기 생성
            previews: list[tuple[str, str]] = []
            for match in pattern.finditer(text):
                if len(previews) >= max_previews:
                    break
                
                original = match.group(0)
                replaced = pattern.sub(rule.replacement, original, count=1)
                previews.append((original, replaced))
            
            return ReplacementResult(
                success=True,
                original_count=original_count,
                replaced_count=original_count,
                preview=previews
            )
            
        except Exception as e:
            return ReplacementResult(
                success=False,
                error_message=str(e)
            )
    
    def replace_text(
        self,
        text: str,
        rule: ReplacementRule
    ) -> tuple[str, int]:
        """
        텍스트 치환
        
        Args:
            text: 원본 텍스트
            rule: 치환 규칙
        
        Returns:
            (치환된 텍스트, 치환 횟수)
        """
        try:
            flags = 0 if rule.case_sensitive else re.IGNORECASE
            
            if rule.is_regex:
                pattern = re.compile(rule.pattern, flags)
            else:
                pattern = re.compile(re.escape(rule.pattern), flags)
            
            result, count = pattern.subn(rule.replacement, text)
            return result, count
            
        except Exception:
            return text, 0
    
    def replace_in_hwp(
        self,
        file_path: str,
        rules: list[ReplacementRule],
        output_path: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> dict[str, Any]:
        """
        HWP 파일 내 텍스트 치환
        
        Args:
            file_path: HWP 파일 경로
            rules: 치환 규칙 목록
            output_path: 출력 경로 (None이면 원본 덮어쓰기)
            progress_callback: 진행률 콜백
        
        Returns:
            치환 결과 {규칙명: 치환횟수}
        """
        results: dict[str, int] = {}
        
        try:
            from .hwp_handler import HwpHandler
            
            with HwpHandler() as handler:
                handler._ensure_hwp()
                hwp = handler._hwp
                
                hwp.open(file_path)
                
                total = len(rules)
                
                for idx, rule in enumerate(rules, start=1):
                    if progress_callback:
                        progress_callback(idx, total, rule.name)
                    
                    # pyhwpx의 찾기/바꾸기 기능 사용
                    try:
                        if rule.is_regex:
                            # 정규식 모드
                            count = hwp.find_replace_regex(
                                rule.pattern,
                                rule.replacement
                            )
                        else:
                            # 일반 텍스트 모드
                            count = hwp.find_replace(
                                rule.pattern,
                                rule.replacement
                            )
                        
                        results[rule.name] = count if count else 0
                        
                    except Exception as e:
                        self._logger.warning(f"규칙 '{rule.name}' 적용 실패: {e}")
                        results[rule.name] = 0
                
                # 저장
                save_path = output_path if output_path else file_path
                hwp.save_as(save_path)
            
        except Exception as e:
            results["_error"] = str(e)
        
        return results
    
    def batch_replace(
        self,
        files: list[str],
        rules: list[ReplacementRule],
        output_dir: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> dict[str, dict[str, int]]:
        """
        여러 파일 일괄 치환
        
        Args:
            files: 파일 경로 목록
            rules: 치환 규칙 목록
            output_dir: 출력 디렉토리 (None이면 원본 덮어쓰기)
            progress_callback: 진행률 콜백
        
        Returns:
            {파일명: {규칙명: 치환횟수}}
        """
        from pathlib import Path
        
        all_results: dict[str, dict[str, int]] = {}
        total = len(files)
        
        for idx, file_path in enumerate(files, start=1):
            filename = Path(file_path).name
            
            if progress_callback:
                progress_callback(idx, total, filename)
            
            if output_dir:
                output_path = str(Path(output_dir) / filename)
            else:
                output_path = None
            
            results = self.replace_in_hwp(file_path, rules, output_path)
            all_results[filename] = results
        
        return all_results
    
    @staticmethod
    def create_masking_rule(
        pattern: str,
        mask_char: str = "*",
        mask_groups: list[int] = None,
        keep_groups: list[int] = None
    ) -> ReplacementRule:
        """
        마스킹 규칙 생성 헬퍼
        
        Args:
            pattern: 정규식 패턴 (그룹 포함)
            mask_char: 마스킹 문자
            mask_groups: 마스킹할 그룹 번호
            keep_groups: 유지할 그룹 번호
        
        Returns:
            ReplacementRule
        """
        # 간단한 구현: 전체를 마스킹
        try:
            compiled = re.compile(pattern)
            num_groups = compiled.groups
            
            replacement_parts = []
            for i in range(1, num_groups + 1):
                if keep_groups and i in keep_groups:
                    replacement_parts.append(f"\\{i}")
                elif mask_groups is None or i in mask_groups:
                    replacement_parts.append(mask_char * 4)  # 기본 4자 마스킹
                else:
                    replacement_parts.append(f"\\{i}")
            
            replacement = "".join(replacement_parts)
            
            return ReplacementRule(
                name="커스텀 마스킹",
                pattern=pattern,
                replacement=replacement,
                is_regex=True
            )
            
        except Exception as e:
            logging.getLogger(__name__).warning(f"마스킹 규칙 생성 중 오류: {e}")
            return ReplacementRule(
                name="커스텀 마스킹",
                pattern=pattern,
                replacement=mask_char * 4,
                is_regex=True
            )

"""
HWP Handler Module
pyhwpx 래퍼 클래스 - HWP 파일 제어

Author: HWP Master
"""

import os
import gc
import re
import logging
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum


class ConvertFormat(Enum):
    """변환 포맷 열거형"""
    PDF = "pdf"
    TXT = "txt"
    HWPX = "hwpx"
    JPG = "jpg"
    HTML = "html"


@dataclass
class ConversionResult:
    """변환 결과 데이터 클래스"""
    success: bool
    source_path: str
    output_path: Optional[str] = None
    error_message: Optional[str] = None


class HwpHandler:
    """
    pyhwpx 래퍼 클래스
    HWP 파일 열기, 변환, 병합, 분할 등의 기능 제공
    """
    
    def __init__(self) -> None:
        self._hwp = None
        self._is_initialized = False
        self._logger = logging.getLogger(__name__)
    
    def _ensure_hwp(self) -> None:
        """pyhwpx 인스턴스 초기화"""
        if self._hwp is None:
            try:
                import pyhwpx
                self._hwp = pyhwpx.Hwp(visible=False)
                self._is_initialized = True
            except ImportError:
                raise RuntimeError("pyhwpx가 설치되어 있지 않습니다. 'pip install pyhwpx'로 설치해주세요.")
            except Exception as e:
                raise RuntimeError(f"한글 프로그램 초기화 실패: {e}")
    
    def close(self) -> None:
        """한글 인스턴스 종료"""
        if self._hwp is not None:
            try:
                self._hwp.quit()
            except Exception as e:
                self._logger.warning(f"HWP 종료 중 오류 (무시됨): {e}")
            finally:
                self._hwp = None
                self._is_initialized = False
                gc.collect()
    
    def __enter__(self):
        self._ensure_hwp()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
    
    # ==================== 변환 기능 ====================
    
    def convert_to_pdf(self, source_path: str, output_path: Optional[str] = None) -> ConversionResult:
        """HWP를 PDF로 변환"""
        return self._convert(source_path, ConvertFormat.PDF, output_path)
    
    def convert_to_txt(self, source_path: str, output_path: Optional[str] = None) -> ConversionResult:
        """HWP를 TXT로 변환"""
        return self._convert(source_path, ConvertFormat.TXT, output_path)
    
    def convert_to_hwpx(self, source_path: str, output_path: Optional[str] = None) -> ConversionResult:
        """HWP를 HWPX로 변환"""
        return self._convert(source_path, ConvertFormat.HWPX, output_path)
    
    def convert_to_jpg(self, source_path: str, output_path: Optional[str] = None) -> ConversionResult:
        """HWP를 JPG로 변환 (첫 페이지)"""
        return self._convert(source_path, ConvertFormat.JPG, output_path)
    
    def _convert(
        self, 
        source_path: str, 
        target_format: ConvertFormat,
        output_path: Optional[str] = None
    ) -> ConversionResult:
        """내부 변환 메서드"""
        try:
            self._ensure_hwp()
            
            source = Path(source_path)
            if not source.exists():
                return ConversionResult(
                    success=False,
                    source_path=source_path,
                    error_message=f"파일이 존재하지 않습니다: {source_path}"
                )
            
            # 출력 경로 결정
            if output_path is None:
                output_path = str(source.with_suffix(f".{target_format.value}"))
            
            # 파일 열기
            self._hwp.open(source_path)
            
            # 포맷별 저장
            format_map = {
                ConvertFormat.PDF: "PDF",
                ConvertFormat.TXT: "TEXT",
                ConvertFormat.HWPX: "HWPX",
                ConvertFormat.JPG: "JPEG",
                ConvertFormat.HTML: "HTML",
            }
            
            save_format = format_map.get(target_format, "PDF")
            self._hwp.save_as(output_path, format=save_format)
            
            return ConversionResult(
                success=True,
                source_path=source_path,
                output_path=output_path
            )
            
        except Exception as e:
            return ConversionResult(
                success=False,
                source_path=source_path,
                error_message=str(e)
            )
    
    def batch_convert(
        self,
        source_files: list[str],
        target_format: ConvertFormat,
        output_dir: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> list[ConversionResult]:
        """
        일괄 변환
        
        Args:
            source_files: 변환할 파일 목록
            target_format: 목표 포맷
            output_dir: 출력 디렉토리 (None이면 원본 위치)
            progress_callback: 진행률 콜백 (current, total, filename)
        
        Returns:
            변환 결과 리스트
        """
        results: list[ConversionResult] = []
        total = len(source_files)
        
        try:
            self._ensure_hwp()
            
            for idx, source_path in enumerate(source_files):
                # 콜백 호출
                if progress_callback:
                    progress_callback(idx + 1, total, Path(source_path).name)
                
                # 출력 경로 결정
                if output_dir:
                    output_path = str(
                        Path(output_dir) / 
                        Path(source_path).with_suffix(f".{target_format.value}").name
                    )
                else:
                    output_path = None
                
                # 변환 실행
                result = self._convert(source_path, target_format, output_path)
                results.append(result)
                
                # 메모리 관리 (100건마다 GC)
                if (idx + 1) % 100 == 0:
                    gc.collect()
            
        except Exception as e:
            # 남은 파일들에 대해 에러 결과 추가
            for remaining in source_files[len(results):]:
                results.append(ConversionResult(
                    success=False,
                    source_path=remaining,
                    error_message=str(e)
                ))
        
        return results
    
    # ==================== 병합 기능 ====================
    
    def merge_files(
        self,
        source_files: list[str],
        output_path: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> ConversionResult:
        """
        여러 HWP 파일을 하나로 병합
        
        Args:
            source_files: 병합할 파일 목록 (순서대로)
            output_path: 출력 파일 경로
            progress_callback: 진행률 콜백
        
        Returns:
            병합 결과
        """
        try:
            self._ensure_hwp()
            
            if len(source_files) < 2:
                return ConversionResult(
                    success=False,
                    source_path=str(source_files),
                    error_message="병합하려면 최소 2개 이상의 파일이 필요합니다."
                )
            
            total = len(source_files)
            
            # 첫 번째 파일 열기
            if progress_callback:
                progress_callback(1, total, Path(source_files[0]).name)
            self._hwp.open(source_files[0])
            
            # 나머지 파일 삽입
            for idx, file_path in enumerate(source_files[1:], start=2):
                if progress_callback:
                    progress_callback(idx, total, Path(file_path).name)
                
                # 문서 끝으로 이동
                self._hwp.move_to_end()
                # 페이지 나누기 삽입
                self._hwp.insert_page_break()
                # 파일 삽입
                self._hwp.insert_file(file_path)
            
            # 저장
            self._hwp.save_as(output_path)
            
            return ConversionResult(
                success=True,
                source_path=str(source_files),
                output_path=output_path
            )
            
        except Exception as e:
            return ConversionResult(
                success=False,
                source_path=str(source_files),
                error_message=str(e)
            )
    
    # ==================== 분할 기능 ====================
    
    @staticmethod
    def parse_page_range(range_str: str, max_page: int) -> list[int]:
        """
        페이지 범위 문자열 파싱
        
        Examples:
            "1-3" -> [1, 2, 3]
            "1,3,5" -> [1, 3, 5]
            "1-3,5,7-9" -> [1, 2, 3, 5, 7, 8, 9]
        
        Args:
            range_str: 페이지 범위 문자열
            max_page: 최대 페이지 수
        
        Returns:
            페이지 번호 리스트
        """
        pages: set[int] = set()
        
        # 공백 제거
        range_str = range_str.replace(" ", "")
        
        # 콤마로 분리
        parts = range_str.split(",")
        
        for part in parts:
            if "-" in part:
                # 범위 처리
                match = re.match(r"(\d+)-(\d+)", part)
                if match:
                    start = int(match.group(1))
                    end = int(match.group(2))
                    for p in range(start, min(end + 1, max_page + 1)):
                        if p >= 1:
                            pages.add(p)
            else:
                # 단일 페이지
                try:
                    p = int(part)
                    if 1 <= p <= max_page:
                        pages.add(p)
                except ValueError:
                    logging.getLogger(__name__).debug(f"페이지 범위 파싱 무시됨: {part}")
        
        return sorted(pages)
    
    def split_file(
        self,
        source_path: str,
        page_ranges: list[str],
        output_dir: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> list[ConversionResult]:
        """
        HWP 파일을 페이지 범위별로 분할
        
        Args:
            source_path: 원본 파일 경로
            page_ranges: 페이지 범위 문자열 리스트 (예: ["1-3", "4-6"])
            output_dir: 출력 디렉토리
            progress_callback: 진행률 콜백
        
        Returns:
            분할 결과 리스트
        """
        results: list[ConversionResult] = []
        
        try:
            self._ensure_hwp()
            
            source = Path(source_path)
            output_directory = Path(output_dir)
            output_directory.mkdir(parents=True, exist_ok=True)
            
            total = len(page_ranges)
            
            for idx, range_str in enumerate(page_ranges, start=1):
                if progress_callback:
                    progress_callback(idx, total, f"분할 {idx}/{total}")
                
                # 원본 다시 열기
                self._hwp.open(source_path)
                
                # 전체 페이지 수 확인
                total_pages = self._hwp.get_page_count()
                
                # 페이지 범위 파싱
                pages = self.parse_page_range(range_str, total_pages)
                
                if not pages:
                    results.append(ConversionResult(
                        success=False,
                        source_path=source_path,
                        error_message=f"유효하지 않은 페이지 범위: {range_str}"
                    ))
                    continue
                
                # 출력 파일명
                output_name = f"{source.stem}_p{pages[0]}-{pages[-1]}.hwp"
                output_path = str(output_directory / output_name)
                
                # 페이지 추출 (역순으로 삭제)
                all_pages = set(range(1, total_pages + 1))
                pages_to_delete = sorted(all_pages - set(pages), reverse=True)
                
                for page in pages_to_delete:
                    self._hwp.delete_page(page)
                
                # 저장
                self._hwp.save_as(output_path)
                
                results.append(ConversionResult(
                    success=True,
                    source_path=source_path,
                    output_path=output_path
                ))
                
        except Exception as e:
            # 실패한 범위에 대해 에러 결과 추가
            for remaining_range in page_ranges[len(results):]:
                results.append(ConversionResult(
                    success=False,
                    source_path=source_path,
                    error_message=str(e)
                ))
        
        return results
    
    # ==================== 데이터 주입 ====================
    
    def inject_data(
        self,
        template_path: str,
        data: dict[str, str],
        output_path: str
    ) -> ConversionResult:
        """
        HWP 템플릿에 데이터 주입
        
        Args:
            template_path: 템플릿 파일 경로
            data: 필드명-값 매핑 딕셔너리
            output_path: 출력 경로
        
        Returns:
            주입 결과
        """
        try:
            self._ensure_hwp()
            
            self._hwp.open(template_path)
            
            # 누름틀(Field)에 데이터 삽입
            failed_fields = []
            for field_name, value in data.items():
                try:
                    self._hwp.put_field_text(field_name, str(value))
                except Exception as e:
                    failed_fields.append(field_name)
                    self._logger.debug(f"필드 '{field_name}' 주입 실패: {e}")
            
            if failed_fields:
                self._logger.info(f"주입되지 않은 필드: {failed_fields}")
            
            self._hwp.save_as(output_path)
            
            return ConversionResult(
                success=True,
                source_path=template_path,
                output_path=output_path
            )
            
        except Exception as e:
            return ConversionResult(
                success=False,
                source_path=template_path,
                error_message=str(e)
            )
    
    def batch_inject_data(
        self,
        template_path: str,
        data_list: list[dict[str, str]],
        output_dir: str,
        filename_field: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> list[ConversionResult]:
        """
        대량 데이터 주입
        
        Args:
            template_path: 템플릿 파일 경로
            data_list: 데이터 리스트
            output_dir: 출력 디렉토리
            filename_field: 파일명으로 사용할 필드 (None이면 순번)
            progress_callback: 진행률 콜백
        
        Returns:
            주입 결과 리스트
        """
        results: list[ConversionResult] = []
        output_directory = Path(output_dir)
        output_directory.mkdir(parents=True, exist_ok=True)
        
        template = Path(template_path)
        total = len(data_list)
        
        try:
            self._ensure_hwp()
            
            for idx, data in enumerate(data_list, start=1):
                if progress_callback:
                    progress_callback(idx, total, f"생성 {idx}/{total}")
                
                # 파일명 결정
                if filename_field and filename_field in data:
                    safe_name = re.sub(r'[<>:"/\\|?*]', '_', str(data[filename_field]))
                    output_name = f"{safe_name}.hwp"
                else:
                    output_name = f"{template.stem}_{idx:04d}.hwp"
                
                output_path = str(output_directory / output_name)
                
                result = self.inject_data(template_path, data, output_path)
                results.append(result)
                
                # 메모리 관리 (100건마다 GC)
                if idx % 100 == 0:
                    gc.collect()
            
        except Exception as e:
            for remaining in data_list[len(results):]:
                results.append(ConversionResult(
                    success=False,
                    source_path=template_path,
                    error_message=str(e)
                ))
        
        return results
    
    # ==================== 메타데이터 정리 ====================
    
    def clean_metadata(
        self,
        source_path: str,
        output_path: Optional[str] = None,
        options: Optional[dict[str, bool]] = None
    ) -> ConversionResult:
        """
        문서 메타데이터 정리
        
        Args:
            source_path: 원본 파일 경로
            output_path: 출력 경로 (None이면 덮어쓰기)
            options: 정리 옵션
                - remove_author: 작성자 정보 제거
                - remove_comments: 메모 제거
                - remove_tracking: 변경 추적 제거
                - set_distribution: 배포용 문서 설정
        
        Returns:
            정리 결과
        """
        default_options = {
            "remove_author": True,
            "remove_comments": True,
            "remove_tracking": True,
            "set_distribution": True,
        }
        
        if options:
            default_options.update(options)
        
        try:
            self._ensure_hwp()
            
            self._hwp.open(source_path)
            
            if default_options["remove_author"]:
                try:
                    self._hwp.set_document_info("author", "")
                    self._hwp.set_document_info("company", "")
                except Exception as e:
                    self._logger.warning(f"작성자 정보 제거 실패: {e}")
            
            if default_options["remove_comments"]:
                try:
                    self._hwp.delete_all_comments()
                except Exception as e:
                    self._logger.warning(f"메모 제거 실패: {e}")
            
            if default_options["remove_tracking"]:
                try:
                    self._hwp.accept_all_changes()
                except Exception as e:
                    self._logger.warning(f"변경 추적 내용 수락 실패: {e}")
            
            if default_options["set_distribution"]:
                try:
                    self._hwp.set_distribution_mode(True)
                except Exception as e:
                    self._logger.warning(f"배포용 문서 설정 실패: {e}")
            
            # 저장
            save_path = output_path if output_path else source_path
            self._hwp.save_as(save_path)
            
            return ConversionResult(
                success=True,
                source_path=source_path,
                output_path=save_path
            )
            
        except Exception as e:
            return ConversionResult(
                success=False,
                source_path=source_path,
                error_message=str(e)
            )

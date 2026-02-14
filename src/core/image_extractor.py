"""
Image Extractor Module
HWP 문서 이미지 추출

Author: HWP Master
"""

import gc
import os
import logging
from pathlib import Path
from typing import Optional, Callable, Any
from dataclasses import dataclass, field
from uuid import uuid4
import zipfile
import shutil


@dataclass
class ImageInfo:
    """추출된 이미지 정보"""
    original_name: str
    saved_path: str
    size_bytes: int
    format: str
    page: int = 0


@dataclass
class ExtractResult:
    """이미지 추출 결과"""
    success: bool
    source_path: str
    images: list[ImageInfo] = field(default_factory=list)
    error_message: Optional[str] = None


class ImageExtractor:
    """이미지 추출기"""
    
    def __init__(self, clipboard_callback: Optional[Callable[[str], bool]] = None) -> None:
        self._hwp: Any = None
        self._is_initialized = False
        self._logger = logging.getLogger(__name__)
        self._clipboard_callback = clipboard_callback
    
    def _ensure_hwp(self) -> None:
        if self._hwp is None:
            try:
                import pyhwpx
                self._hwp = pyhwpx.Hwp(visible=False)
                self._is_initialized = True
            except ImportError:
                raise RuntimeError("pyhwpx가 설치되어 있지 않습니다.")
            except Exception as e:
                raise RuntimeError(f"한글 프로그램 초기화 실패: {e}")

    def _get_hwp(self) -> Any:
        """초기화된 HWP 인스턴스 반환"""
        self._ensure_hwp()
        if self._hwp is None:
            raise RuntimeError("한글 인스턴스 초기화 실패")
        return self._hwp
    
    def close(self) -> None:
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
    
    def extract_images(
        self,
        source_path: str,
        output_dir: str,
        prefix: str = "",
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> ExtractResult:
        """
        문서 내 모든 이미지 추출
        
        Args:
            source_path: 원본 HWP 파일 경로
            output_dir: 이미지 저장 폴더
            prefix: 파일명 접두사
            progress_callback: 진행률 콜백
        
        Returns:
            추출 결과
        """
        try:
            hwp = self._get_hwp()
            
            source = Path(source_path)
            if not source.exists():
                return ExtractResult(False, source_path, error_message="파일 없음")
            
            output_directory = Path(output_dir)
            output_directory.mkdir(parents=True, exist_ok=True)
            
            # 기본 전략: HWP -> 임시 HWPX로 저장 후 ZIP(BinData)에서 추출
            hwp.open(source_path)

            temp_hwpx = output_directory / f".tmp_{uuid4().hex}.hwpx"
            images: list[ImageInfo] = []
            try:
                hwp.save_as(str(temp_hwpx), format="HWPX")
                images = self._extract_from_hwpx_zip(
                    temp_hwpx,
                    output_directory,
                    prefix=prefix,
                    source_stem=source.stem,
                    progress_callback=progress_callback,
                )
            finally:
                try:
                    if temp_hwpx.exists():
                        temp_hwpx.unlink()
                except Exception:
                    pass

            # 보조 전략: (선택) 컨트롤 순회/클립보드 방식
            # 클립보드 콜백이 없는 환경에서는 성공 가능성이 낮아 기본적으로는 시도하지 않음.
            if not images and self._clipboard_callback:
                try:
                    images = self._extract_from_controls(source, output_directory, prefix, progress_callback)
                except Exception as e:
                    self._logger.debug(f"컨트롤 기반 추출 실패(무시됨): {e}")

            if progress_callback:
                progress_callback(len(images), len(images), "완료")

            return ExtractResult(True, source_path, images)
            
        except Exception as e:
            return ExtractResult(False, source_path, error_message=str(e))

    def _extract_from_hwpx_zip(
        self,
        hwpx_path: Path,
        output_dir: Path,
        *,
        prefix: str,
        source_stem: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> list[ImageInfo]:
        """HWPX(ZIP) 구조에서 BinData 이미지를 추출"""
        images: list[ImageInfo] = []

        with zipfile.ZipFile(hwpx_path, "r") as zf:
            names = [
                name for name in zf.namelist()
                if name.startswith("BinData/") and any(
                    name.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]
                )
            ]

            total = len(names)
            for idx, name in enumerate(names, start=1):
                if progress_callback:
                    progress_callback(idx, total, f"이미지 {idx}/{total}")

                ext = Path(name).suffix.lower()
                if prefix:
                    new_name = f"{prefix}_{idx:03d}{ext}"
                else:
                    new_name = f"{source_stem}_{idx:03d}{ext}"

                save_path = output_dir / new_name

                with zf.open(name) as src, open(save_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)

                if save_path.exists():
                    images.append(ImageInfo(
                        original_name=name,
                        saved_path=str(save_path),
                        size_bytes=save_path.stat().st_size,
                        format=ext,
                    ))

        return images

    def _extract_from_controls(
        self,
        source: Path,
        output_directory: Path,
        prefix: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> list[ImageInfo]:
        """(보조) 컨트롤 순회 + 클립보드 콜백을 이용한 이미지 추출"""
        hwp = self._get_hwp()
        hwp.open(str(source))

        images: list[ImageInfo] = []
        image_count = 0

        ctrl: Any = hwp.HeadCtrl
        while ctrl:
            if ctrl.UserDesc in ["그림", "OLE개체", "그리기개체"]:
                image_count += 1
                if progress_callback:
                    progress_callback(image_count, -1, f"이미지 {image_count}")

                if prefix:
                    filename = f"{prefix}_{image_count:03d}"
                else:
                    filename = f"{source.stem}_{image_count:03d}"

                saved_path = self._extract_single_image(ctrl, output_directory, filename)
                if saved_path and os.path.exists(saved_path):
                    file_size = os.path.getsize(saved_path)
                    file_ext = Path(saved_path).suffix.lower()
                    images.append(ImageInfo(
                        original_name=ctrl.UserDesc,
                        saved_path=saved_path,
                        size_bytes=file_size,
                        format=file_ext,
                    ))

            ctrl = ctrl.Next

        return images
    
    def _extract_single_image(self, ctrl: Any, output_dir: Path, filename: str) -> Optional[str]:
        """단일 이미지 추출"""
        try:
            hwp = self._get_hwp()
            # 그림 컨트롤 선택
            ctrl.Select()
            
            # 이미지 데이터 가져오기
            pset = hwp.HParameterSet.HShapeObject
            hwp.HAction.GetDefault("ShapeObjAttrDialog", pset.HSet)
            
            # 그림 저장
            image_path = str(output_dir / f"{filename}.png")
            
            # SaveAs 또는 클립보드를 통한 저장
            try:
                hwp.HAction.Run("Copy")
                # 클립보드에서 이미지 저장
                self._save_clipboard_image(image_path)
                return image_path
            except Exception as e:
                self._logger.debug(f"클립보드 방식 이미지 추출 실패: {e}")
            
            return None
            
        except Exception as e:
            self._logger.debug(f"_extract_single_image 실패: {e}")
            return None
    
    def _save_clipboard_image(self, output_path: str) -> bool:
        """클립보드 이미지 저장"""
        try:
            # PySide6 dependency removed from Core module
            
            if self._clipboard_callback:
                return self._clipboard_callback(output_path)
            
            self._logger.warning("클립보드 저장 콜백이 설정되지 않았습니다.")
            return False
        except Exception as e:
            self._logger.warning(f"클립보드 저장 실패: {e}")
            return False
    
    # Backward compatible helper
    def _extract_from_hwpx(self, source_path: str, output_dir: Path, prefix: str) -> list[ImageInfo]:
        """HWP를 임시 HWPX로 변환 후 ZIP(BinData)에서 추출"""
        try:
            hwp = self._get_hwp()
            hwp.open(source_path)

            temp_hwpx = output_dir / f".tmp_{uuid4().hex}.hwpx"
            try:
                hwp.save_as(str(temp_hwpx), format="HWPX")
                return self._extract_from_hwpx_zip(
                    temp_hwpx,
                    output_dir,
                    prefix=prefix,
                    source_stem=Path(source_path).stem,
                )
            finally:
                try:
                    if temp_hwpx.exists():
                        temp_hwpx.unlink()
                except Exception as e:
                    self._logger.debug(f"임시 HWPX 삭제 실패(무시): {temp_hwpx} ({e})")
        except Exception as e:
            self._logger.warning(f"HWPX(ZIP) 추출 실패: {e}")
            return []
    
    def batch_extract(
        self,
        source_files: list[str],
        output_dir: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> list[ExtractResult]:
        """일괄 이미지 추출"""
        results: list[ExtractResult] = []
        total = len(source_files)
        
        try:
            self._ensure_hwp()
            
            for idx, source_path in enumerate(source_files):
                if progress_callback:
                    progress_callback(idx + 1, total, Path(source_path).name)
                
                # 파일별 폴더 생성
                from ..utils.filename_sanitizer import sanitize_filename

                base = sanitize_filename(Path(source_path).stem)
                file_output_dir = Path(output_dir) / base
                if file_output_dir.exists():
                    # Avoid mixing outputs when multiple inputs share the same stem.
                    for i in range(1, 10_000):
                        cand = Path(output_dir) / f"{base}_{i}"
                        if not cand.exists():
                            file_output_dir = cand
                            break
                
                result = self.extract_images(source_path, str(file_output_dir))
                results.append(result)
                
                if (idx + 1) % 20 == 0:
                    gc.collect()
                    
        except Exception as e:
            for remaining in source_files[len(results):]:
                results.append(ExtractResult(
                    success=False,
                    source_path=remaining,
                    error_message=str(e)
                ))
        
        return results
    
    def get_image_count(self, source_path: str) -> int:
        """문서 내 이미지 개수 반환"""
        try:
            hwp = self._get_hwp()
            hwp.open(source_path)
            
            count = 0
            ctrl: Any = hwp.HeadCtrl
            
            while ctrl:
                if ctrl.UserDesc in ["그림", "OLE개체", "그리기개체"]:
                    count += 1
                ctrl = ctrl.Next
            
            return count
        except Exception as e:
            self._logger.warning(f"이미지 개수 계산 실패: {source_path} ({e})", exc_info=True)
            return 0

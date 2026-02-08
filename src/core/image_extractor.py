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
            
            hwp.open(source_path)
            
            images: list[ImageInfo] = []
            image_count = 0
            
            try:
                # 컨트롤 순회하며 이미지 찾기
                ctrl: Any = hwp.HeadCtrl
                
                while ctrl:
                    if ctrl.UserDesc in ["그림", "OLE개체", "그리기개체"]:
                        image_count += 1
                        
                        if progress_callback:
                            progress_callback(image_count, -1, f"이미지 {image_count}")
                        
                        try:
                            # 이미지 저장
                            if prefix:
                                filename = f"{prefix}_{image_count:03d}"
                            else:
                                filename = f"{source.stem}_{image_count:03d}"
                            
                            # 이미지 추출 시도
                            saved_path = self._extract_single_image(ctrl, output_directory, filename)
                            
                            if saved_path and os.path.exists(saved_path):
                                file_size = os.path.getsize(saved_path)
                                file_ext = Path(saved_path).suffix.lower()
                                
                                images.append(ImageInfo(
                                    original_name=ctrl.UserDesc,
                                    saved_path=saved_path,
                                    size_bytes=file_size,
                                    format=file_ext
                                ))
                        except Exception as e:
                            self._logger.debug(f"이미지 {image_count} 추출 실패: {e}")
                    
                    ctrl = ctrl.Next
                    
            except Exception as e:
                self._logger.warning(f"컨트롤 순회 방식 실패, HWPX 방법 시도: {e}")
                images = self._extract_from_hwpx(source_path, output_directory, prefix)
            
            if progress_callback:
                progress_callback(len(images), len(images), "완료")
            
            return ExtractResult(True, source_path, images)
            
        except Exception as e:
            return ExtractResult(False, source_path, error_message=str(e))
    
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
    
    def _extract_from_hwpx(self, source_path: str, output_dir: Path, prefix: str) -> list[ImageInfo]:
        """HWPX(ZIP) 구조에서 이미지 추출"""
        import zipfile
        import shutil
        
        images: list[ImageInfo] = []
        
        try:
            hwp = self._get_hwp()
            # HWP를 HWPX로 임시 변환
            temp_hwpx = output_dir / f"_temp_{Path(source_path).stem}.hwpx"
            hwp.save_as(str(temp_hwpx), format="HWPX")
            
            # HWPX는 ZIP 포맷
            with zipfile.ZipFile(temp_hwpx, 'r') as zf:
                for name in zf.namelist():
                    if name.startswith("BinData/") and any(name.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']):
                        # 이미지 추출
                        ext = Path(name).suffix
                        image_num = len(images) + 1
                        
                        if prefix:
                            new_name = f"{prefix}_{image_num:03d}{ext}"
                        else:
                            new_name = f"image_{image_num:03d}{ext}"
                        
                        save_path = output_dir / new_name
                        
                        with zf.open(name) as src, open(save_path, 'wb') as dst:
                            shutil.copyfileobj(src, dst)
                        
                        if save_path.exists():
                            images.append(ImageInfo(
                                original_name=name,
                                saved_path=str(save_path),
                                size_bytes=save_path.stat().st_size,
                                format=ext
                            ))
            
            # 임시 파일 삭제
            if temp_hwpx.exists():
                temp_hwpx.unlink()
                
        except Exception as e:
            self._logger.warning(f"HWPX 추출 실패: {e}")
        
        return images
    
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
                file_output_dir = Path(output_dir) / Path(source_path).stem
                
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
        except Exception:
            return 0

"""
HWP Handler Module
pyhwpx ?섑띁 ?대옒??- HWP ?뚯씪 ?쒖뼱

Author: HWP Master
"""

import os
import gc
import re
import logging
from pathlib import Path
from typing import Optional, Callable, Any, Iterable, Iterator
from dataclasses import dataclass
from enum import Enum


class ConvertFormat(Enum):
    """蹂???щ㎎ ?닿굅??"""
    PDF = "pdf"
    TXT = "txt"
    HWPX = "hwpx"
    JPG = "jpg"
    HTML = "html"


@dataclass
class ConversionResult:
    """蹂??寃곌낵 ?곗씠???대옒??"""
    success: bool
    source_path: str
    output_path: Optional[str] = None
    error_message: Optional[str] = None


class HwpHandler:
    """
    pyhwpx ?섑띁 ?대옒??
    HWP ?뚯씪 ?닿린, 蹂?? 蹂묓빀, 遺꾪븷 ?깆쓽 湲곕뒫 ?쒓났
    """
    
    def __init__(self) -> None:
        self._hwp: Any = None
        self._is_initialized = False
        self._logger = logging.getLogger(__name__)
    
    def _ensure_hwp(self) -> None:
        """pyhwpx ?몄뒪?댁뒪 珥덇린??"""
        if self._hwp is None:
            try:
                import pyhwpx
                self._hwp = pyhwpx.Hwp(visible=False)
                self._is_initialized = True
            except ImportError:
                raise RuntimeError("pyhwpx媛 ?ㅼ튂?섏뼱 ?덉? ?딆뒿?덈떎. 'pip install pyhwpx'濡??ㅼ튂?댁＜?몄슂.")
            except Exception as e:
                raise RuntimeError(f"?쒓? ?꾨줈洹몃옩 珥덇린???ㅽ뙣: {e}")

    def _get_hwp(self) -> Any:
        """珥덇린?붾맂 HWP ?몄뒪?댁뒪 諛섑솚"""
        self._ensure_hwp()
        if self._hwp is None:
            raise RuntimeError("?쒓? ?몄뒪?댁뒪 珥덇린???ㅽ뙣")
        return self._hwp
    
    def close(self) -> None:
        """?쒓? ?몄뒪?댁뒪 醫낅즺"""
        if self._hwp is not None:
            try:
                self._hwp.quit()
            except Exception as e:
                self._logger.warning(f"HWP 醫낅즺 以??ㅻ쪟 (臾댁떆??: {e}")
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
    
    # ==================== 蹂??湲곕뒫 ====================
    
    def convert_to_pdf(self, source_path: str, output_path: Optional[str] = None) -> ConversionResult:
        """HWP瑜?PDF濡?蹂??"""
        return self._convert(source_path, ConvertFormat.PDF, output_path)
    
    def convert_to_txt(self, source_path: str, output_path: Optional[str] = None) -> ConversionResult:
        """HWP瑜?TXT濡?蹂??"""
        return self._convert(source_path, ConvertFormat.TXT, output_path)
    
    def convert_to_hwpx(self, source_path: str, output_path: Optional[str] = None) -> ConversionResult:
        """HWP瑜?HWPX濡?蹂??"""
        return self._convert(source_path, ConvertFormat.HWPX, output_path)
    
    def convert_to_jpg(self, source_path: str, output_path: Optional[str] = None) -> ConversionResult:
        """HWP瑜?JPG濡?蹂??(泥??섏씠吏)"""
        return self._convert(source_path, ConvertFormat.JPG, output_path)

    def convert(
        self,
        source_path: str,
        target_format: ConvertFormat,
        output_path: Optional[str] = None,
    ) -> ConversionResult:
        """Public convert API (worker?먯꽌 private _convert 吏곸젒 ?몄텧 諛⑹?)."""
        return self._convert(source_path, target_format, output_path)
    
    def _convert(
        self, 
        source_path: str, 
        target_format: ConvertFormat,
        output_path: Optional[str] = None
    ) -> ConversionResult:
        """?대? 蹂??硫붿꽌??"""
        try:
            hwp = self._get_hwp()
            
            source = Path(source_path)
            if not source.exists():
                return ConversionResult(
                    success=False,
                    source_path=source_path,
                    error_message=f"?뚯씪??議댁옱?섏? ?딆뒿?덈떎: {source_path}"
                )
            
            # 異쒕젰 寃쎈줈 寃곗젙
            if output_path is None:
                output_path = str(source.with_suffix(f".{target_format.value}"))
            
            # ?뚯씪 ?닿린
            hwp.open(source_path)
            
            # ?щ㎎蹂????
            format_map = {
                ConvertFormat.PDF: "PDF",
                ConvertFormat.TXT: "TEXT",
                ConvertFormat.HWPX: "HWPX",
                ConvertFormat.JPG: "JPEG",
                ConvertFormat.HTML: "HTML",
            }
            
            save_format = format_map.get(target_format, "PDF")
            hwp.save_as(output_path, format=save_format)
            
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
        ?쇨큵 蹂??
        
        Args:
            source_files: 蹂?섑븷 ?뚯씪 紐⑸줉
            target_format: 紐⑺몴 ?щ㎎
            output_dir: 異쒕젰 ?붾젆?좊━ (None?대㈃ ?먮낯 ?꾩튂)
            progress_callback: 吏꾪뻾瑜?肄쒕갚 (current, total, filename)
        
        Returns:
            蹂??寃곌낵 由ъ뒪??
        """
        results: list[ConversionResult] = []
        total = len(source_files)
        
        try:
            hwp = self._get_hwp()
            
            for idx, source_path in enumerate(source_files):
                # 肄쒕갚 ?몄텧
                if progress_callback:
                    progress_callback(idx + 1, total, Path(source_path).name)
                
                # 異쒕젰 寃쎈줈 寃곗젙
                if output_dir:
                    from ..utils.output_paths import resolve_output_path

                    output_path = resolve_output_path(
                        output_dir,
                        source_path,
                        new_ext=target_format.value,
                    )
                else:
                    output_path = None
                
                # 蹂???ㅽ뻾
                result = self._convert(source_path, target_format, output_path)
                results.append(result)
                
                # 硫붾え由?愿由?(100嫄대쭏??GC)
                if (idx + 1) % 100 == 0:
                    gc.collect()
            
        except Exception as e:
            # ?⑥? ?뚯씪?ㅼ뿉 ????먮윭 寃곌낵 異붽?
            for remaining in source_files[len(results):]:
                results.append(ConversionResult(
                    success=False,
                    source_path=remaining,
                    error_message=str(e)
                ))
        
        return results
    
    # ==================== 蹂묓빀 湲곕뒫 ====================
    
    def merge_files(
        self,
        source_files: list[str],
        output_path: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> ConversionResult:
        """
        ?щ윭 HWP ?뚯씪???섎굹濡?蹂묓빀
        
        Args:
            source_files: 蹂묓빀???뚯씪 紐⑸줉 (?쒖꽌?濡?
            output_path: 異쒕젰 ?뚯씪 寃쎈줈
            progress_callback: 吏꾪뻾瑜?肄쒕갚
        
        Returns:
            蹂묓빀 寃곌낵
        """
        try:
            hwp = self._get_hwp()
            
            if len(source_files) < 2:
                return ConversionResult(
                    success=False,
                    source_path=str(source_files),
                    error_message="蹂묓빀?섎젮硫?理쒖냼 2媛??댁긽???뚯씪???꾩슂?⑸땲??"
                )
            
            total = len(source_files)
            
            # 泥?踰덉㎏ ?뚯씪 ?닿린
            if progress_callback:
                progress_callback(1, total, Path(source_files[0]).name)
            hwp.open(source_files[0])
            
            # ?섎㉧吏 ?뚯씪 ?쎌엯
            for idx, file_path in enumerate(source_files[1:], start=2):
                if progress_callback:
                    progress_callback(idx, total, Path(file_path).name)
                
                # 臾몄꽌 ?앹쑝濡??대룞 (pyhwpx Run ?≪뀡 ?ъ슜)
                hwp.Run("MoveDocEnd")
                # ?섏씠吏 ?섎늻湲??쎌엯 (pyhwpx Run ?≪뀡 ?ъ슜)
                hwp.Run("BreakPage")
                # ?뚯씪 ?쎌엯 (InsertFile ?≪뀡 ?ъ슜)
                hwp.Run("InsertFile")
                hwp.HParameterSet.HInsertFile.filename = file_path
                hwp.HAction.Execute("InsertFile", hwp.HParameterSet.HInsertFile.HSet)
            
            # ???
            hwp.save_as(output_path)
            
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
    
    # ==================== 遺꾪븷 湲곕뒫 ====================
    
    @staticmethod
    def parse_page_range(range_str: str, max_page: int) -> list[int]:
        """
        ?섏씠吏 踰붿쐞 臾몄옄???뚯떛
        
        Examples:
            "1-3" -> [1, 2, 3]
            "1,3,5" -> [1, 3, 5]
            "1-3,5,7-9" -> [1, 2, 3, 5, 7, 8, 9]
        
        Args:
            range_str: ?섏씠吏 踰붿쐞 臾몄옄??
            max_page: 理쒕? ?섏씠吏 ??
        
        Returns:
            ?섏씠吏 踰덊샇 由ъ뒪??
        """
        pages: set[int] = set()
        
        # 怨듬갚 ?쒓굅
        range_str = range_str.replace(" ", "")
        
        # 肄ㅻ쭏濡?遺꾨━
        parts = range_str.split(",")
        
        for part in parts:
            if "-" in part:
                # 踰붿쐞 泥섎━
                match = re.match(r"(\d+)-(\d+)", part)
                if match:
                    start = int(match.group(1))
                    end = int(match.group(2))
                    for p in range(start, min(end + 1, max_page + 1)):
                        if p >= 1:
                            pages.add(p)
            else:
                # ?⑥씪 ?섏씠吏
                try:
                    p = int(part)
                    if 1 <= p <= max_page:
                        pages.add(p)
                except ValueError:
                    logging.getLogger(__name__).debug(f"?섏씠吏 踰붿쐞 ?뚯떛 臾댁떆?? {part}")
        
        return sorted(pages)
    
    def split_file(
        self,
        source_path: str,
        page_ranges: list[str],
        output_dir: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> list[ConversionResult]:
        """
        HWP ?뚯씪???섏씠吏 踰붿쐞蹂꾨줈 遺꾪븷
        
        Args:
            source_path: ?먮낯 ?뚯씪 寃쎈줈
            page_ranges: ?섏씠吏 踰붿쐞 臾몄옄??由ъ뒪??(?? ["1-3", "4-6"])
            output_dir: 異쒕젰 ?붾젆?좊━
            progress_callback: 吏꾪뻾瑜?肄쒕갚
        
        Returns:
            遺꾪븷 寃곌낵 由ъ뒪??
        """
        results: list[ConversionResult] = []
        
        try:
            hwp = self._get_hwp()
            
            source = Path(source_path)
            output_directory = Path(output_dir)
            output_directory.mkdir(parents=True, exist_ok=True)
            
            total = len(page_ranges)
            
            for idx, range_str in enumerate(page_ranges, start=1):
                if progress_callback:
                    progress_callback(idx, total, f"遺꾪븷 {idx}/{total}")
                
                try:
                    # ?먮낯 ?ㅼ떆 ?닿린
                    hwp.open(source_path)
                    
                    # ?꾩껜 ?섏씠吏 ???뺤씤 (pyhwpx ?띿꽦 ?ъ슜)
                    total_pages = hwp.PageCount
                    
                    # ?섏씠吏 踰붿쐞 ?뚯떛
                    pages = self.parse_page_range(range_str, total_pages)
                    
                    if not pages:
                        results.append(ConversionResult(
                            success=False,
                            source_path=source_path,
                            error_message=f"?좏슚?섏? ?딆? ?섏씠吏 踰붿쐞: {range_str}"
                        ))
                        continue
                    
                    # 異쒕젰 ?뚯씪紐?
                    output_name = f"{source.stem}_p{pages[0]}-{pages[-1]}.hwp"
                    output_path = str(output_directory / output_name)
                    
                    # ?섏씠吏 異붿텧: ?먰븯???섏씠吏留??④린怨????
                    # pyhwpx?먯꽌 ?섏씠吏 ??젣瑜??꾪빐 ??닚?쇰줈 遺덊븘?뷀븳 ?섏씠吏 ??젣
                    all_pages = set(range(1, total_pages + 1))
                    pages_to_delete = sorted(all_pages - set(pages), reverse=True)
                    
                    for page in pages_to_delete:
                        # ?대떦 ?섏씠吏濡??대룞 ???섏씠吏 ?꾩껜 ?좏깮?섏뿬 ??젣
                        try:
                            # ?섏씠吏 ?대룞 (pyhwpx Run ?≪뀡 ?ъ슜)
                            hwp.Run("MoveDocBegin")
                            for _ in range(page - 1):
                                hwp.Run("MovePageDown")
                            # ?섏씠吏 踰붿쐞 ?좏깮 諛???젣
                            hwp.Run("MovePageBegin")
                            hwp.Run("MoveSelPageDown")
                            hwp.Run("Delete")
                        except Exception as del_e:
                            self._logger.warning(f"?섏씠吏 {page} ??젣 以??ㅻ쪟 (臾댁떆??: {del_e}")
                            hwp.Run("Cancel")  # ?좏깮 ?댁젣
                    
                    # ???
                    hwp.save_as(output_path)
                    
                    results.append(ConversionResult(
                        success=True,
                        source_path=source_path,
                        output_path=output_path
                    ))
                    
                except Exception as inner_e:
                    results.append(ConversionResult(
                        success=False,
                        source_path=source_path,
                        error_message=str(inner_e)
                    ))
                
        except Exception as e:
            # ?ㅽ뙣??踰붿쐞??????먮윭 寃곌낵 異붽?
            for remaining_range in page_ranges[len(results):]:
                results.append(ConversionResult(
                    success=False,
                    source_path=source_path,
                    error_message=str(e)
                ))
        
        return results
    
    # ==================== ?곗씠??二쇱엯 ====================
    
    def inject_data(
        self,
        template_path: str,
        data: dict[str, str],
        output_path: str
    ) -> ConversionResult:
        """
        HWP ?쒗뵆由우뿉 ?곗씠??二쇱엯
        
        Args:
            template_path: ?쒗뵆由??뚯씪 寃쎈줈
            data: ?꾨뱶紐?媛?留ㅽ븨 ?뺤뀛?덈━
            output_path: 異쒕젰 寃쎈줈
        
        Returns:
            二쇱엯 寃곌낵
        """
        try:
            hwp = self._get_hwp()
            
            hwp.open(template_path)
            
            # ?꾨쫫?(Field)???곗씠???쎌엯
            failed_fields = []
            for field_name, value in data.items():
                try:
                    hwp.put_field_text(field_name, str(value))
                except Exception as e:
                    failed_fields.append(field_name)
                    self._logger.debug(f"?꾨뱶 '{field_name}' 二쇱엯 ?ㅽ뙣: {e}")
            
            if failed_fields:
                self._logger.info(f"二쇱엯?섏? ?딆? ?꾨뱶: {failed_fields}")
            
            hwp.save_as(output_path)
            
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
        ????곗씠??二쇱엯
        
        Args:
            template_path: ?쒗뵆由??뚯씪 寃쎈줈
            data_list: ?곗씠??由ъ뒪??
            output_dir: 異쒕젰 ?붾젆?좊━
            filename_field: ?뚯씪紐낆쑝濡??ъ슜???꾨뱶 (None?대㈃ ?쒕쾲)
            progress_callback: 吏꾪뻾瑜?肄쒕갚
        
        Returns:
            二쇱엯 寃곌낵 由ъ뒪??
        """
        results: list[ConversionResult] = []

        try:
            for result in self.iter_inject_data(
                template_path=template_path,
                data_iterable=data_list,
                output_dir=output_dir,
                filename_field=filename_field,
                progress_callback=progress_callback,
                total_count=len(data_list),
            ):
                results.append(result)

        except Exception as e:
            for _ in data_list[len(results):]:
                results.append(ConversionResult(
                    success=False,
                    source_path=template_path,
                    error_message=str(e)
                ))

        return results

    def iter_inject_data(
        self,
        template_path: str,
        data_iterable: Iterable[dict[str, str]],
        output_dir: str,
        filename_field: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        total_count: Optional[int] = None,
    ) -> Iterator[ConversionResult]:
        """Streaming data-injection API to avoid loading all rows in memory."""
        output_directory = Path(output_dir)
        output_directory.mkdir(parents=True, exist_ok=True)

        template = Path(template_path)
        try:
            total = int(total_count) if total_count is not None else len(data_iterable)  # type: ignore[arg-type]
        except Exception:
            total = -1

        self._ensure_hwp()

        for idx, data in enumerate(data_iterable, start=1):
            if progress_callback:
                progress_callback(idx, total, f"?앹꽦 {idx}/{total if total > 0 else '?'}")

            if filename_field and filename_field in data:
                from ..utils.filename_sanitizer import sanitize_filename

                safe_name = sanitize_filename(str(data[filename_field]))
                output_name = f"{safe_name}.hwp"
            else:
                output_name = f"{template.stem}_{idx:04d}.hwp"

            output_path = str(output_directory / output_name)
            yield self.inject_data(template_path, data, output_path)

            if idx % 100 == 0:
                gc.collect()

    def clean_metadata(
        self,
        source_path: str,
        output_path: Optional[str] = None,
        options: Optional[dict[str, bool]] = None
    ) -> ConversionResult:
        """
        臾몄꽌 硫뷀??곗씠???뺣━
        
        Args:
            source_path: ?먮낯 ?뚯씪 寃쎈줈
            output_path: 異쒕젰 寃쎈줈 (None?대㈃ ??뼱?곌린)
            options: ?뺣━ ?듭뀡
                - remove_author: ?묒꽦???뺣낫 ?쒓굅
                - remove_comments: 硫붾え ?쒓굅
                - remove_tracking: 蹂寃?異붿쟻 ?쒓굅
                - set_distribution: 諛고룷??臾몄꽌 ?ㅼ젙
        
        Returns:
            ?뺣━ 寃곌낵
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
            hwp = self._get_hwp()
            
            hwp.open(source_path)
            
            if default_options["remove_author"]:
                try:
                    hwp.set_document_info("author", "")
                    hwp.set_document_info("company", "")
                except Exception as e:
                    self._logger.warning(f"?묒꽦???뺣낫 ?쒓굅 ?ㅽ뙣: {e}")
            
            if default_options["remove_comments"]:
                try:
                    hwp.delete_all_comments()
                except Exception as e:
                    self._logger.warning(f"硫붾え ?쒓굅 ?ㅽ뙣: {e}")
            
            if default_options["remove_tracking"]:
                try:
                    hwp.accept_all_changes()
                except Exception as e:
                    self._logger.warning(f"蹂寃?異붿쟻 ?댁슜 ?섎씫 ?ㅽ뙣: {e}")
            
            if default_options["set_distribution"]:
                try:
                    hwp.set_distribution_mode(True)
                except Exception as e:
                    self._logger.warning(f"諛고룷??臾몄꽌 ?ㅼ젙 ?ㅽ뙣: {e}")
            
            # ???
            save_path = output_path if output_path else source_path
            hwp.save_as(save_path)
            
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


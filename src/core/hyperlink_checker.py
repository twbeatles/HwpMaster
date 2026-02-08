"""
Hyperlink Checker Module
HWP 문서 하이퍼링크 검사

Author: HWP Master
"""

import gc
import logging
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum


class LinkStatus(Enum):
    """링크 상태"""
    VALID = "valid"
    BROKEN = "broken"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"
    LOCAL_MISSING = "local_missing"
    LOCAL_OK = "local_ok"


@dataclass
class LinkInfo:
    """링크 정보"""
    url: str
    text: str
    page: int
    status: LinkStatus = LinkStatus.UNKNOWN
    error_message: str = ""


@dataclass
class LinkCheckResult:
    """링크 검사 결과"""
    success: bool
    source_path: str
    links: list[LinkInfo] = field(default_factory=list)
    valid_count: int = 0
    broken_count: int = 0
    error_message: Optional[str] = None


class HyperlinkChecker:
    """하이퍼링크 검사기"""
    
    def __init__(self) -> None:
        self._hwp: Any = None
        self._is_initialized = False
        self._logger = logging.getLogger(__name__)
        self._timeout = 5  # 초
    
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
    
    def extract_links(self, source_path: str) -> LinkCheckResult:
        """문서 내 모든 링크 추출"""
        try:
            hwp = self._get_hwp()
            source = Path(source_path)
            if not source.exists():
                return LinkCheckResult(False, source_path, error_message="파일 없음")
            
            hwp.open(source_path)
            links: list[LinkInfo] = []
            
            try:
                ctrl: Any = hwp.HeadCtrl
                while ctrl:
                    if ctrl.UserDesc == "하이퍼링크":
                        try:
                            url = str(ctrl.GetSetItem("HyperLink"))
                            text = str(ctrl.GetSetItem("Text") or url)
                            links.append(LinkInfo(url=url, text=text, page=0))
                        except Exception as e:
                            self._logger.warning(f"하이퍼링크 정보 추출 실패: {e}")
                    ctrl = ctrl.Next
            except Exception as e:
                self._logger.warning(f"하이퍼링크 컨트롤 탐색 중 오류: {e}")
            
            return LinkCheckResult(True, source_path, links)
        except Exception as e:
            return LinkCheckResult(False, source_path, error_message=str(e))
    
    def check_url(self, url: str) -> tuple[LinkStatus, str]:
        """URL 유효성 검사"""
        if url.startswith("file://") or url.startswith("/") or (len(url) > 1 and url[1] == ":"):
            return self._check_local_file(url)
        
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=self._timeout) as response:
                if response.status < 400:
                    return LinkStatus.VALID, ""
                else:
                    return LinkStatus.BROKEN, f"HTTP {response.status}"
        except urllib.error.HTTPError as e:
            return LinkStatus.BROKEN, f"HTTP {e.code}"
        except urllib.error.URLError as e:
            return LinkStatus.BROKEN, str(e.reason)
        except TimeoutError:
            return LinkStatus.TIMEOUT, "연결 시간 초과"
        except Exception as e:
            return LinkStatus.UNKNOWN, str(e)
    
    def _check_local_file(self, path: str) -> tuple[LinkStatus, str]:
        """로컬 파일 경로 검사"""
        try:
            if path.startswith("file:///"):
                path = path[8:]
            elif path.startswith("file://"):
                path = path[7:]
            
            if Path(path).exists():
                return LinkStatus.LOCAL_OK, ""
            else:
                return LinkStatus.LOCAL_MISSING, "파일 없음"
        except Exception as e:
            return LinkStatus.UNKNOWN, str(e)
    
    def check_links(
        self,
        source_path: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> LinkCheckResult:
        """문서 내 모든 링크 추출 및 검사"""
        result = self.extract_links(source_path)
        if not result.success:
            return result
        
        total = len(result.links)
        valid_count = 0
        broken_count = 0
        
        for idx, link in enumerate(result.links):
            if progress_callback:
                progress_callback(idx + 1, total, link.url[:50])
            
            status, error = self.check_url(link.url)
            link.status = status
            link.error_message = error
            
            if status in [LinkStatus.VALID, LinkStatus.LOCAL_OK]:
                valid_count += 1
            elif status in [LinkStatus.BROKEN, LinkStatus.LOCAL_MISSING, LinkStatus.TIMEOUT]:
                broken_count += 1
        
        result.valid_count = valid_count
        result.broken_count = broken_count
        return result
    
    def generate_report(self, result: LinkCheckResult, output_path: str) -> bool:
        """HTML 리포트 생성"""
        try:
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>링크 검사 리포트</title>
<style>
body {{ font-family: 'Segoe UI', sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }}
h1 {{ color: #333; }} .summary {{ background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
.valid {{ color: #22c55e; }} .broken {{ color: #ef4444; }} .unknown {{ color: #f59e0b; }}
</style></head><body>
<h1>🔗 링크 검사 리포트</h1>
<div class="summary">
<p><strong>파일:</strong> {Path(result.source_path).name}</p>
<p><strong>총 링크:</strong> {len(result.links)}개</p>
<p><strong>유효:</strong> <span class="valid">{result.valid_count}개</span> | 
<strong>오류:</strong> <span class="broken">{result.broken_count}개</span></p>
</div>
<table><tr><th>상태</th><th>URL</th><th>텍스트</th><th>오류</th></tr>"""
            
            for link in result.links:
                status_class = "valid" if link.status in [LinkStatus.VALID, LinkStatus.LOCAL_OK] else "broken" if link.status in [LinkStatus.BROKEN, LinkStatus.LOCAL_MISSING] else "unknown"
                status_text = "✓" if status_class == "valid" else "✗" if status_class == "broken" else "?"
                html += f'<tr><td class="{status_class}">{status_text}</td><td>{link.url}</td><td>{link.text}</td><td>{link.error_message}</td></tr>'
            
            html += "</table></body></html>"
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html)
            return True
        except Exception:
            return False

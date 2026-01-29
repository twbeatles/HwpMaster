# CLAUDE.md - HWP Master 프로젝트 가이드

## 📋 프로젝트 개요

**HWP Master**는 pyhwpx 기반 경량 HWP 업무 자동화 도구입니다.

### 핵심 원칙
- **경량화**: Pandas/NumPy 사용 금지, openpyxl만 허용
- **타입 힌팅**: 모든 함수에 Python 타입 힌트 필수
- **에러 처리**: try-except 블록으로 견고한 예외 처리

---

## 🏗️ 아키텍처

```
src/
├── core/           # 비즈니스 로직 (hwp_handler, excel_handler 등)
├── ui/             # PySide6 인터페이스
│   ├── pages/      # 단위 페이지 (home_page, convert_page 등)
│   └── widgets/    # 재사용 위젯 (file_list, progress_card 등)
└── utils/          # 유틸리티 (worker, logger, settings)
```

### 핵심 모듈

| 모듈 | 역할 | 의존성 |
|------|------|--------|
| `hwp_handler.py` | HWP 파일 조작 | pyhwpx |
| `excel_handler.py` | Excel/CSV 처리 | openpyxl |
| `template_store.py` | 템플릿 관리 | - |
| `macro_recorder.py` | 매크로 기록/재생 | - |
| `regex_replacer.py` | 정규식 치환 | re |
| `style_cop.py` | 서식 통일 | - |
| `table_doctor.py` | 표 스타일 수정 | - |
| `doc_diff.py` | 문서 비교 | difflib |
| `smart_toc.py` | 목차 생성 | re |
| `watermark_manager.py` | 워터마크 삽입 | - |
| `header_footer_manager.py` | 헤더/푸터 관리 | - |
| `bookmark_manager.py` | 북마크 관리 | - |
| `hyperlink_checker.py` | 하이퍼링크 검사 | urllib |
| `image_extractor.py` | 이미지 추출 | - |

---

## 🎯 개발 가이드라인

### 코드 스타일
```python
# 타입 힌트 필수
def process_file(file_path: str, options: dict[str, Any]) -> Optional[str]:
    """함수 설명."""
    pass

# dataclass 활용
@dataclass
class ResultInfo:
    success: bool
    file_path: str
    error_message: Optional[str] = None
```

### UI 패턴
```python
# 페이지 구조
class FeaturePage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        # 레이아웃 설정
        pass
```

### 백그라운드 작업
```python
# utils/worker.py의 BaseWorker 상속
class CustomWorker(BaseWorker):
    def run(self) -> None:
        # 시그널로 진행률 전달
        self.progress.emit(current, total, status)
```

---

## 📁 파일 위치 규칙

| 파일 유형 | 위치 |
|-----------|------|
| 새 코어 모듈 | `src/core/` |
| 새 UI 페이지 | `src/ui/pages/` |
| 재사용 위젯 | `src/ui/widgets/` |
| 스타일시트 | `assets/styles/` |

---

## ⚠️ 금지 사항

1. **Pandas/NumPy 사용 금지** - openpyxl로 대체
2. **전역 상태 사용 금지** - 클래스 기반 설계
3. **하드코딩된 경로 금지** - `Path` 사용
4. **TODO/FIXME 주석 금지** - 완전한 코드 작성

---

## 🔧 테스트 명령어

```bash
# 모듈 임포트 테스트
python -c "from src.core import *; from src.ui.pages import *; print('OK')"

# 앱 실행
python main.py
```

---

## 📝 변경 시 체크리스트

- [ ] 타입 힌트 추가됨
- [ ] docstring 작성됨
- [ ] 에러 처리 완료됨
- [ ] `__init__.py` 업데이트됨
- [ ] 사이드바 메뉴 추가됨 (UI 추가 시)

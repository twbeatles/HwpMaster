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
## 📂 프로젝트 구조

```
hwp-master/
├── main.py                    # 프로그램 진입점
├── requirements.txt           # 의존성 패키지 목록
├── hwp_master.spec            # PyInstaller 빌드 설정
├── assets/
│   └── styles/style.qss       # 다크모드 스타일시트
├── src/
│   ├── core/                  # 핵심 비즈니스 로직
│   │   ├── hwp_handler.py     # HWP 제어 (pyhwpx)
│   │   ├── action_runner.py   # 범용 액션 실행기 (Run/Execute)
│   │   ├── capability_mapper.py # pyhwpx 기능 커버리지 매퍼
│   │   ├── excel_handler.py   # Excel 처리 (openpyxl)
│   │   ├── template_store.py  # 템플릿 관리
│   │   ├── macro_recorder.py  # 매크로 기록/재생
│   │   ├── regex_replacer.py  # 정규식 치환
│   │   ├── style_cop.py       # 서식 교정
│   │   ├── table_doctor.py    # 표 스타일 수정
│   │   ├── doc_diff.py        # 문서 비교
│   │   ├── smart_toc.py       # 목차 생성
│   │   ├── watermark_manager.py   # 워터마크 관리
│   │   ├── header_footer_manager.py # 헤더/푸터 관리
│   │   ├── bookmark_manager.py    # 북마크 관리
│   │   ├── hyperlink_checker.py   # 링크 검사
│   │   └── image_extractor.py     # 이미지 추출
│   ├── ui/                    # 사용자 인터페이스
│   │   ├── main_window.py     # 메인 윈도우 프레임
│   │   ├── pages/             # 기능별 페이지
│   │   │   ├── home_page.py        # 홈 대시보드
│   │   │   ├── convert_page.py     # 변환
│   │   │   ├── merge_split_page.py # 병합/분할
│   │   │   ├── data_inject_page.py # 데이터 주입
│   │   │   ├── metadata_page.py    # 메타정보
│   │   │   ├── template_page.py    # 템플릿
│   │   │   ├── macro_page.py       # 매크로
│   │   │   ├── regex_page.py       # 정규식
│   │   │   ├── style_cop_page.py   # 서식 교정
│   │   │   ├── table_doctor_page.py # 표 교정
│   │   │   ├── doc_diff_page.py    # 문서 비교
│   │   │   ├── smart_toc_page.py   # 목차
│   │   │   ├── watermark_page.py   # 워터마크
│   │   │   ├── header_footer_page.py # 헤더/푸터
│   │   │   ├── bookmark_page.py    # 북마크
│   │   │   ├── hyperlink_page.py   # 링크 검사
│   │   │   ├── image_extractor_page.py # 이미지 추출
│   │   │   ├── action_console_page.py # 고급 액션 콘솔
│   │   │   └── settings_page.py    # 설정
│   │   └── widgets/           # 공통 위젯
│   │       ├── file_list.py        # 파일 목록
│   │       ├── feature_card.py     # 기능 카드
│   │       ├── progress_card.py    # 진행률 표시
│   │       ├── sidebar_button.py   # 사이드바 버튼
│   │       ├── page_header.py      # 페이지 헤더
│   │       ├── toast.py            # 알림 메시지
│   │       ├── favorites_panel.py  # 즐겨찾기 패널
│   │       └── history_panel.py    # 작업 히스토리
│   └── utils/                 # 유틸리티
│       ├── worker.py          # 백그라운드 작업 (QThread)
│       ├── logger.py          # 로깅 시스템
│       ├── settings.py        # 설정 관리
│       ├── theme_manager.py   # 테마 관리
│       └── history_manager.py # 히스토리 관리
└── tests/                     # 단위 테스트
```

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

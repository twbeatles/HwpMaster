# GEMINI.md - HWP Master 프로젝트 컨텍스트

## 🎯 프로젝트 목적

**HWP Master**는 pyhwpx 기반 경량 HWP 업무 자동화 도구입니다.  
공공기관/기업의 HWP 문서 작업을 자동화하여 업무 효율성을 높입니다.

---

## 🏗️ 기술 스택

| 카테고리 | 기술 | 비고 |
|----------|------|------|
| GUI | PySide6 | Qt 바인딩 |
| HWP 제어 | pyhwpx | 한글 COM 래퍼 |
| Excel | openpyxl | Pandas 대체 |
| 스타일 | QSS | 다크모드 |

---

## 📂 핵심 파일

### 코어 모듈 (`src/core/`)
- `hwp_handler.py` - HWP 파일 조작 (변환, 병합, 분할)
- `action_runner.py` - 범용 Run/Execute 액션 실행 및 프리셋
- `capability_mapper.py` - pyhwpx 기능 커버리지 매핑
- `excel_handler.py` - Excel/CSV 읽기/쓰기
- `template_store.py` - 내장 템플릿 관리
- `macro_recorder.py` - 매크로 기록/재생
- `regex_replacer.py` - 정규식 치환 (11종 프리셋)
- `style_cop.py` - 서식 통일 (4종 프리셋)
- `table_doctor.py` - 표 스타일 수정
- `doc_diff.py` - 문서 비교 (difflib)
- `smart_toc.py` - 자동 목차 생성
- `watermark_manager.py` - 워터마크 삽입
- `header_footer_manager.py` - 헤더/푸터 관리
- `bookmark_manager.py` - 북마크 관리
- `hyperlink_checker.py` - 하이퍼링크 검사
- `image_extractor.py` - 이미지 추출

### UI 모듈 (`src/ui/`)
- `main_window.py` - 메인 윈도우 프레임
- `pages/`
  - `home_page.py`, `convert_page.py`, `merge_split_page.py`
  - `data_inject_page.py`, `metadata_page.py`, `settings_page.py`
  - `template_page.py`, `macro_page.py`, `regex_page.py`
  - `style_cop_page.py`, `table_doctor_page.py`, `doc_diff_page.py`
  - `smart_toc_page.py`, `watermark_page.py`, `header_footer_page.py`
  - `bookmark_page.py`, `hyperlink_page.py`, `image_extractor_page.py`
- `widgets/`
  - `file_list.py`, `progress_card.py`, `feature_card.py`
  - `sidebar_button.py`, `toast.py`, `page_header.py`
  - `favorites_panel.py`, `history_panel.py`

### 유틸리티 (`src/utils/`)
- `worker.py` - 백그라운드 작업 (QThread)
- `logger.py` - 로깅 시스템
- `settings.py` - 설정 관리
- `theme_manager.py` - 테마 관리
- `history_manager.py` - 작업 히스토리

---

## 🎨 UI 및 프로젝트 구조

```
HwpMaster/
├── main.py                    # 프로그램 진입점
├── requirements.txt           # 의존성 패키지 목록
├── hwp_master.spec            # PyInstaller 빌드 설정
├── assets/
│   └── styles/style.qss       # 다크모드 스타일시트
├── src/
│   ├── core/                  # 핵심 비즈니스 로직
│   │   ├── hwp_handler.py     # HWP 제어 (pyhwpx)
│   │   ├── action_runner.py   # 범용 액션 실행기
│   │   ├── capability_mapper.py # pyhwpx 기능 커버리지 매핑
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

## ⚠️ 개발 규칙

### 필수 사항
1. **타입 힌트**: 모든 함수에 적용
2. **dataclass**: 데이터 구조체에 사용
3. **Context Manager**: HWP 핸들러에 `with` 문 사용
4. **에러 처리**: try-except로 안전하게 처리

### 금지 사항
1. ❌ Pandas/NumPy 사용
2. ❌ 전역 변수 사용
3. ❌ TODO/FIXME 주석
4. ❌ 하드코딩된 파일 경로

---

## 🔧 자주 사용하는 명령어

```bash
# 의존성 설치
pip install -r requirements.txt

# 앱 실행
python main.py

# 모듈 테스트
python -c "from src.core import *; print('Core OK')"
python -c "from src.ui.pages import *; print('Pages OK')"
```

---

## 📝 새 기능 추가 시

1. `src/core/` 에 비즈니스 로직 모듈 생성
2. `src/core/__init__.py` 에 export 추가
3. `src/ui/pages/` 에 UI 페이지 생성
4. `src/ui/pages/__init__.py` 에 export 추가
5. `main_window.py` 사이드바에 메뉴 추가
6. `main_window.py` 페이지 스택에 위젯 추가

---

## 🧪 검증 방법

```bash
# 전체 모듈 임포트 테스트
python -c "
from src.core import HwpHandler, ExcelHandler
from src.core import TemplateStore, MacroRecorder, RegexReplacer
from src.core import StyleCop, TableDoctor, DocDiff, SmartTOC
from src.ui.pages import HomePage, ConvertPage, MergeSplitPage, DataInjectPage
from src.ui.pages import TemplatePage, MacroPage, RegexPage
from src.ui.pages import StyleCopPage, TableDoctorPage, DocDiffPage, SmartTocPage
print('All modules OK')
"
```

---

## 📌 운영 정합성 메모 (2026-02-27)

- 최신 회귀 기준:
  - `pytest -q` => `57 passed, 2 skipped`
- 매크로 녹화 구현 범위:
  - `Macro Page`의 녹화 시작/종료 UI + `Action Console` 성공 실행 명령 기록(`run_action`, `execute_action`)
- 저장 정책 기본값:
  - Action Console/북마크 삭제 계열은 기본 **원본 보존(새 파일 저장)**, 덮어쓰기는 명시 선택 시만 허용
- Smart TOC 분석 정책:
  - form-feed 기반 페이지 추정 + HWPX 스타일 힌트 보조 분석(실패 시 패턴 기반 폴백)

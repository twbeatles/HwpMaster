# HWP Master

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![PySide6](https://img.shields.io/badge/PySide6-6.0+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

**pyhwpx 기반 경량 HWP 업무 자동화 올인원 도구**

HWP Master는 한글(HWP) 문서 작업을 자동화하여 업무 효율을 극대화하는 윈도우용 데스크톱 애플리케이션입니다.

## ✨ 주요 특징

- **🪶 경량화**: Pandas/NumPy 등 무거운 라이브러리 없이 순수 Python으로 최적화
- **🎨 모던 UI**: PySide6 기반의 세련된 다크모드 대시보드 제공
- **🔧 올인원**: 변환, 병합, 분할, 데이터 주입, 서식 교정 등 필수 기능 통합
- **⚡ 고성능**: pyhwpx 기반의 빠른 처리 속도와 안정적인 자동화
- **🛡️ 안전성**: 메타데이터 정리, 배포용 설정, 변경 추적 정리 기능 제공

---

## 📋 시스템 요구사항

| 항목 | 필수 사양 |
|------|----------|
| **OS** | Windows 10/11 (64bit) |
| **소프트웨어** | **한글 2018 이상 설치 필수** (자동화를 위해 필요) |
| **Python** | Python 3.9 이상 |

---

## 🚀 설치 및 실행 방법

### 1. 개발 환경 설정

```bash
# 저장소 클론
git clone https://github.com/twbeatles/HwpMaster.git
cd HwpMaster

# 가상환경 생성 (선택)
python -m venv venv
.\venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 프로그램 실행

```bash
python main.py
```

### 3. 단독 실행 파일(EXE) 빌드

```bash
# PyInstaller로 EXE 파일 생성
pyinstaller hwp_master.spec
```
빌드 완료 후 `dist/HWP_Master` 폴더에서 실행 파일을 확인할 수 있습니다.

---

## 🎯 전체 기능 소개

### 1️⃣ 문서 변환 및 관리 (Core)
| 기능 | 설명 |
|------|------|
| **일괄 변환 (Batch Converter)** | HWP 파일을 PDF, TXT, HWPX, JPG 이미지로 일괄 변환합니다. |
| **병합/분할 (Merge & Split)** | 여러 HWP 문서를 하나로 합치거나, 페이지 단위로 쪼갤 수 있습니다. |
| **문서 초기화** | 문서 내부 정보를 정리하고 누름틀을 초기화합니다. |

### 2️⃣ 데이터 자동화 (Data)
| 기능 | 설명 |
|------|------|
| **데이터 주입 (Data Injector)** | 엑셀/CSV 데이터를 HWP 누름틀에 자동 주입합니다. 완전 빈 행만 스킵하며, 출력 파일명 충돌 시 자동 suffix(`_1`, `_2`...)를 붙여 원본 덮어쓰기를 방지합니다. |
| **메타정보 정리** | 문서 작성자, 회사명, 최종 저장 등의 메타데이터를 일괄 삭제하거나 수정합니다. |

### 3️⃣ 서식 및 스타일 (Style)
| 기능 | 설명 |
|------|------|
| **서식 교정 (Style Cop)** | 문서 내 모든 폰트, 줄간격, 자간을 설정된 표준 양식으로 강제 통일합니다. |
| **표 스타일 수정 (Table Doctor)** | 표의 테두리 두께, 셀 여백, 배경색 등을 일괄 변경합니다. |
| **헤더/푸터 관리** | 머리말, 꼬리말, 쪽 번호를 일괄 적용하거나 삭제합니다. |

### 4️⃣ 고급 편집 도구 (Advanced)
| 기능 | 설명 |
|------|------|
| **템플릿 스토어** | 8종의 내장 양식(휴가계, 지출결의서 등)을 제공하며, **사용자 지정 파일 등록**도 가능합니다. |
| **매크로 레코더** | 수동 매크로 생성/프리셋 실행뿐 아니라, Action Console 실행 흐름을 **녹화 시작/종료**로 기록해 재실행 가능한 매크로로 저장할 수 있습니다. |
| **정규식 치환** | 주민번호, 전화번호, 이메일 등 민감 정보를 패턴 기반으로 마스킹 처리합니다. |
| **문서 비교 (Doc Diff)** | 두 문서의 내용을 비교하여 차이점을 상세한 HTML 리포트로 생성합니다. |
| **스마트 목차 (Smart TOC)** | form-feed(`\\f`) 기반 페이지 분할로 페이지 번호를 추정하고, 가능 시 HWPX 스타일 힌트를 보조 사용해 목차 정확도를 높입니다(실패 시 패턴 기반 자동 폴백). |

### 5️⃣ 유틸리티 (Utils)
| 기능 | 설명 |
|------|------|
| **워터마크** | 텍스트 또는 이미지 워터마크를 투명도 설정과 함께 일괄 삽입합니다. |
| **이미지 추출** | 문서 내 포함된 모든 이미지를 원본 화질로 추출합니다. |
| **링크 검사** | 문서 내 하이퍼링크가 유효한지 검사하고 결과를 엑셀로 내보냅니다. |
| **북마크 관리** | 북마크 추출/내보내기, 전체 삭제, **선택 행만 삭제**를 지원합니다. 삭제 기본값은 새 파일 저장(원본 보존)이며, 명시적으로만 덮어쓰기합니다. |

---

## 📝 사용 가이드

### 💡 사용자 템플릿 등록하기
1. 사이드바에서 `📦 템플릿` 메뉴 선택
2. '내장 템플릿' 카드 중 파일이 없는 항목 선택 (예: '연차휴가 신청서')
3. `파일 등록` 버튼을 눌러 내 컴퓨터의 HWP 양식 파일 선택
4. 이제부터 해당 템플릿을 바로 생성하여 사용할 수 있습니다.

### 💡 매크로 프리셋 사용하기
1. 사이드바에서 `🎬 매크로` 메뉴 선택
2. `새 매크로` -> `프리셋에서 가져오기` 클릭
3. '공백 정리', '특수문자 통일' 등 원하는 기능 선택
4. `저장` 후 매크로 목록에서 실행

### 💡 Action Console 실행을 매크로로 녹화하기
1. 사이드바에서 `🎬 매크로` 메뉴에서 `녹화 시작` 클릭
2. `🧰 액션 콘솔`에서 JSON 액션 실행
3. 매크로 페이지로 돌아와 `녹화 종료/저장` 클릭 후 이름 입력
4. 저장된 매크로를 목록에서 즉시 재실행

---

## 📁 프로젝트 구조

```
HwpMaster/
├── main.py                    # 프로그램 진입점
├── requirements.txt           # 의존성 패키지 목록
├── hwp_master.spec            # PyInstaller 빌드 설정
├── assets/
│   └── styles/
│       ├── style.template.qss # 템플릿(토큰) 기반 스타일시트(테마 프리셋 적용)
│       └── style.qss          # 레거시/폴백 스타일시트
├── src/
│   ├── core/                  # 핵심 비즈니스 로직
│   │   ├── hwp_handler.py     # HWP 제어 (pyhwpx)
│   │   ├── action_runner.py   # 범용 Run/Execute 액션 실행기
│   │   ├── capability_mapper.py # pyhwpx 커버리지/능력 매핑
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

## 📚 문서

- 코딩 가이드: `CLAUDE.md`
- 종합 감사 문서: `PROJECT_AUDIT_PYHWPX.md`
- 기능 구현 감사/개선: `FEATURE_IMPLEMENTATION_AUDIT_2026-02-28.md`

---

## ⚠️ 주의사항

- **한글 자동화 보안 모듈**: 처음 실행 시 보안 모듈 승인 팝업이 뜰 수 있습니다. '승인'을 선택해주세요.
- **백그라운드 실행**: 대량 변환 시 한글(hwp.exe)이 백그라운드에서 실행됩니다. 작업 도중 강제 종료하면 한글 프로세스가 남을 수 있습니다.

---

## 📄 라이선스

이 프로젝트는 [MIT License](LICENSE)를 따릅니다. 누구나 자유롭게 수정 및 배포할 수 있습니다.

## 최근 업데이트 (2026-02-25)

- 메타정보 정리 기능 확장
  - 작성자/주석/변경추적/배포옵션 선택 적용
  - 개인정보 패턴 스캔(주민번호/연락처/이메일 등)
  - 문서 암호 설정(환경 지원 시) + strict 실패 옵션
- 데이터 주입 기능 확장
  - 파일명 생성 필드 지정
  - 파일명 템플릿 지정 (`{부서}_{성명}_{index}` 형식)
- 코어 API 확장
  - `HwpHandler.harden_document`, `scan_personal_info`, `list_fields`, `fill_fields`, `get_meta_tags`, `set_meta_tags`, `mail_merge`

## 최근 업데이트 (2026-02-25, Phase 3/4)

- Phase 3: `execute_action` 기반 빌트인 프리셋 추가
  - `table_professional_style`, `table_dense_grid`
  - `shape_presentation_emphasis`
  - `image_print_enhance`, `image_watermark_light`
  - Action Console에서 프리셋을 JSON으로 불러오기/즉시 실행 가능
- Phase 4: 실문서 기반 정확도 보강 테스트 추가
  - `tests/test_real_hwp_doc_diff_smart_toc.py`
  - 실제 HWP 문서를 생성해 `DocDiff.compare`, `SmartTOC.extract_toc` 검증
  - 기본은 skip, 실행 시 `HWPMASTER_REAL_DOC_TESTS=1` 필요

## 최근 업데이트 (2026-02-27)

- 품질게이트/회귀 안정화
  - QSS 테스트를 테마 토큰 기반 검증으로 전환
- 데이터 주입 안정성 강화
  - CSV 완전 빈 행만 스킵
  - 출력 파일명 충돌 시 자동 suffix 부여
  - 결과 데이터에 `skipped_empty_rows`, `filename_collisions` 포함
- 매크로/북마크 실기능 확장
  - Action Console 실행 명령 녹화 및 매크로 저장
  - 북마크 선택 삭제(`delete_selected`) 구현
- Smart TOC/보안 개선
  - form-feed 기반 페이지 추정 및 `analysis_mode` 제공
  - Doc Diff HTML escape 처리 강화
- 저장 정책 정리(원본 보존 기본)
  - Action Console: `저장 안 함` / `새 파일 저장(기본)` / `원본 덮어쓰기`
  - 북마크 삭제: 기본 새 파일 저장, 덮어쓰기는 명시 선택 시만 허용
- 회귀 테스트(2026-02-27 기준)
  - `pytest -q`: `57 passed, 2 skipped`

## 최근 업데이트 (2026-02-28)

- 기능 구현 감사(섹션 2) 반영 완료
  - 매크로 저장 ID를 `macro_<uuid4hex>`로 전환하여 동시 저장 충돌 제거
  - Header/Footer, Watermark Worker의 partial failure를 `success=False`로 정정
  - remove 모드 출력 경로를 `resolve_output_path()`로 통일해 basename 충돌 회피
  - Excel 행 스킵 정책을 "행 전체가 빈 값일 때만 스킵"으로 통일
  - Hyperlink 리포트 저장 실패를 실패 카운트/최종 실패로 반영
- 회귀 테스트
  - `pytest -q`: `65 passed, 2 skipped`

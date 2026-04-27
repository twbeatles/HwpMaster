# GEMINI.md - HWP Master 프로젝트 컨텍스트

## 🎯 프로젝트 목적

**HWP Master**는 pyhwpx 기반 자동화와 rhwp 기반 내장 편집기를 결합한 경량 HWP 업무 도구입니다.
공공기관/기업의 HWP 문서 작업을 자동화하면서도, 무거운 데이터 처리 스택 없이 Windows 데스크톱 환경에서 안정적으로 동작하고, 기본 문서 편집 워크스페이스까지 제공하는 것을 목표로 합니다.

---

## 🏗️ 기술 스택 / 기준 버전

| 카테고리 | 기술 | 비고 |
|----------|------|------|
| Runtime | Python 3.10+ | `pyrightconfig.json` 기준 |
| GUI | PySide6 >= 6.6.0 | Qt 바인딩 |
| HWP 제어 | pyhwpx >= 0.5.0 | 한글 COM 래퍼 |
| 내장 편집기 | rhwp / QtWebEngine | `@rhwp/core 0.7.6` WASM self-host |
| Excel | openpyxl >= 3.1.0 | Pandas 대체 |
| 정적 분석 | Pyright / Pylance | `pyright .` clean 유지 |
| 텍스트 규칙 | `.editorconfig` | UTF-8 / LF 고정 |

---

## 📂 핵심 파일

### 루트
- `main.py` - 앱 진입점, 스타일시트/폰트/메인 윈도우 초기화
- `hwp_master.spec` - PyInstaller 빌드 설정
- `pyrightconfig.json` - 정적 분석 범위와 Python 버전 기준
- `.editorconfig` - 인코딩/줄바꿈/들여쓰기 기준
- `PROJECT_AUDIT_PYHWPX.md` - 저장소 전반 감사와 기능 구현 후속 정리
- `FUNCTIONAL_IMPLEMENTATION_AUDIT_2026-04-19.md` - 2026-04-19 기능 구현 감사 후속 반영 기록
- `scripts/verify_core_modules.py` - 핵심 모듈 임포트 검증
- `scripts/perf_smoke.py` - 수동 성능 스모크 테스트
- `assets/rhwp_studio/` - 내장 rhwp 편집기 정적 앱과 WASM 런타임
- `vendor/rhwp/` - rhwp 0.7.6 기준 npm 산출물과 라이선스 메타데이터

### 코어 모듈 (`src/core/`)
- `hwp_handler/` - HWP 파일 조작 파사드와 내부 도메인 모듈
- `editor/` - rhwp 편집 세션, 저장 정책, localhost asset/API 서버
- `action_runner/` - 범용 `run_action` / `execute_action` 실행 및 프리셋 패키지
- `hyperlink_checker.py` - 링크 검사와 `LinkInfo` 결과 타입 정의
- `template_store/`, `macro_recorder/` - 템플릿/매크로 저장소 패키지
- `doc_diff/`, `smart_toc.py` - 비교/목차 생성
- `watermark_manager.py`, `header_footer_manager.py`, `bookmark_manager.py`, `image_extractor.py`

### UI 모듈 (`src/ui/`)
- `main_window/` - 페이지 lazy-loading, 사이드바/스택 구성 패키지
- `pages/` - 기능별 페이지 구현
- `widgets/` - 재사용 가능한 공통 위젯

### 유틸리티 (`src/utils/`)
- `worker/` - 백그라운드 작업과 결과 집계 패키지
- `atomic_write.py` - 설정/메타데이터 원자적 저장
- `output_paths.py` - 출력 경로/충돌 회피 정책
- `filename_sanitizer.py` - 안전한 파일명 생성
- `qss_renderer.py` - 테마 토큰 기반 QSS 생성
- `com_init.py` - COM 초기화 보조
- `task_tracking.py` - 최근 파일/작업 이력 기록 헬퍼
- `version.py`, `settings.py`, `theme_manager.py`, `logger.py`, `history_manager.py`

---

## ⚠️ 개발 규칙

### 필수 사항
1. 모든 함수와 핵심 멤버에 타입 힌트를 적용합니다.
2. Qt Optional 객체는 명시적으로 좁혀서 다룹니다.
3. 워커 결과 타입은 UI까지 동일한 구조로 전달합니다.
4. 저장 경로와 충돌 회피 로직은 공통 유틸리티를 재사용합니다.
5. 로그, 오류 메시지, docstring은 UTF-8 한국어 기준으로 정리합니다.
6. 설정/히스토리/매크로/템플릿 메타데이터 쓰기는 `atomic_write.py` 기반으로 유지합니다.
7. 홈 대시보드에 노출되는 최근 파일/작업 이력 갱신은 `task_tracking.py`를 재사용합니다.
8. 내장 편집기 저장은 `EditorSaveService`를 통해 백업/복구/HWPX 보호 정책을 적용합니다.

### 금지 사항
1. ❌ Pandas/NumPy 추가
2. ❌ 근거 없는 `Any` 남발
3. ❌ TODO/FIXME 주석 방치
4. ❌ 하드코딩된 절대 경로
5. ❌ 깨진 한글 문자열 커밋

---

## 🔧 자주 사용하는 명령어

```bash
pip install -r requirements.txt
python main.py
pyright .
pytest -q
HWPMASTER_REAL_DOC_TESTS=1 pytest -q tests/test_real_hwp_doc_diff_smart_toc.py tests/test_real_hwp_feature_smoke.py
python scripts/verify_core_modules.py
python scripts/perf_smoke.py
```

---

## 📝 새 기능 추가 시

1. `src/core/`에 비즈니스 로직을 추가합니다.
2. 필요하면 `src/core/__init__.py` export를 갱신합니다.
3. `src/ui/pages/`에 대응 페이지를 추가합니다.
4. `src/ui/pages/__init__.py` lazy export와 `src/ui/main_window/` 페이지 로딩을 갱신합니다.
5. 워커가 필요하면 `src/utils/worker/` 패턴을 재사용합니다.
6. rhwp/QtWebEngine 편집기 기능이면 `assets/rhwp_studio/`, `vendor/rhwp/`, `hwp_master.spec` 정합성을 함께 확인합니다.
7. `pyright .`와 `pytest -q`를 통과시킨 뒤 문서를 업데이트합니다.

---

## 🧪 현재 검증 기준 (2026-04-27)

- `pyright .` => `0 errors, 0 warnings`
- `pytest -q` => `106 passed, 6 skipped`
- `python scripts/verify_core_modules.py` => 통과
- `pyinstaller hwp_master.spec --noconfirm` => 통과
- 당시 정합성 반영:
  - `src/core/editor/`에 편집 세션/저장 서비스/localhost API 서버 추가
  - `src/ui/pages/editor_page.py`와 `src/ui/main_window/` lazy-loading 경로에 문서 편집 페이지 추가
  - `assets/rhwp_studio/`에 HWP Master용 rhwp bridge UI와 WASM 런타임 포함
  - `vendor/rhwp/`에 upstream `v0.7.6` 기준과 MIT 라이선스 보관
  - HWP 저장 백업, HWPX overwrite 보호, 복구본 저장 테스트 추가
  - `.gitignore`에 rhwp vendor scratch/build artifact 제외 정책 추가

---

## 🧪 현재 검증 기준 (2026-04-19)

- `pyright .` => `0 errors, 0 warnings`
- `pytest -q` => `100 passed, 6 skipped`
- `HWPMASTER_REAL_DOC_TESTS=1 pytest -q tests/test_real_hwp_doc_diff_smart_toc.py tests/test_real_hwp_feature_smoke.py` => 현재 런타임 `6 skipped`
- 인코딩 정리 완료:
  - `src/utils/worker/__init__.py`
  - `src/core/hwp_handler/__init__.py`
- 최신 정합성 반영:
  - `CapabilityMapper` fallback을 복구해 pyhwpx 비가용 환경에서도 카테고리 커버리지를 유지
  - repo-local `pyhwpx` stub(`typings/pyhwpx`)과 `pyrightconfig.json` 정리로 정적 분석 기준 복구
  - `TemplateStoreError`를 도입해 템플릿 등록/추가/삭제/생성의 파일 I/O 실패를 UI-safe 하게 통일
  - 링크 검사는 메모리 결과만 수집하고, HTML/XLSX 저장은 Export 시점으로 분리
  - 취소 작업을 `cancelled` 상태로 히스토리에 기록하고 홈 대시보드에 상태 배지를 표시
  - 설정 페이지에 환경 진단 워커/UI를 추가
  - `hwp_master.spec`는 최신 기능 감사 문서를 조건부 번들링
  - `atomic_write.py`를 통해 settings/history/action-template/template-store/macro 저장을 원자적으로 처리
  - `task_tracking.py`로 최근 파일/작업 히스토리 갱신 로직을 통일
  - 홈 페이지에 최근 작업/즐겨찾기 패널을 추가하고 동일 config dir의 히스토리를 재사용
  - 템플릿 출력 확장자를 원본 suffix와 일치시키고 필드 입력 기반 생성 흐름을 명시
  - Smart TOC HTML 출력의 escape/page 번호 표기와 style-hint 정렬 통계를 보강
  - `ActionRunner` handler 타입을 `Protocol` 기반으로 정리
  - 링크 검사 결과 타입을 `(filename, LinkInfo)`로 고정
  - `QApplication.instance()`와 Qt 레이아웃 접근의 Optional 추론 문제 해소
  - `tests/test_repository_text_integrity.py`로 UTF-8/모지바케 회귀 방지
  - `tests/test_same_path_package_facades.py`로 same-path package facade 회귀 방지

---

## 📌 운영 메모

- 전역 상태는 원칙적으로 지양하지만, 매크로 녹화는 `Action Console`과 `Macro Page` 간 세션 공유를 위해 예외적으로 공유 상태를 사용합니다.
- 편집성 기능은 기본적으로 **원본 보존(새 파일 저장)** 정책을 따릅니다.
- 내장 편집기의 `저장`은 현재 문서 경로에 쓰되 최초 덮어쓰기 전 백업을 생성하며, `복구본 저장`은 사용자 config dir의 recovery 경로에 기록합니다.
- EXE 빌드는 `hwp_master.spec` 기준이며 결과물은 `dist/` 아래에 생성됩니다.
- typing stub(`typings/pyhwpx`)은 개발용 정적 분석 자산이며 EXE 번들 대상은 아닙니다.

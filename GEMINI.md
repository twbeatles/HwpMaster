# GEMINI.md - HWP Master 프로젝트 컨텍스트

## 🎯 프로젝트 목적

**HWP Master**는 pyhwpx 기반 경량 HWP 업무 자동화 도구입니다.
공공기관/기업의 HWP 문서 작업을 자동화하면서도, 무거운 데이터 처리 스택 없이 Windows 데스크톱 환경에서 안정적으로 동작하는 것을 목표로 합니다.

---

## 🏗️ 기술 스택 / 기준 버전

| 카테고리 | 기술 | 비고 |
|----------|------|------|
| Runtime | Python 3.10+ | `pyrightconfig.json` 기준 |
| GUI | PySide6 >= 6.6.0 | Qt 바인딩 |
| HWP 제어 | pyhwpx >= 0.5.0 | 한글 COM 래퍼 |
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
- `scripts/verify_core_modules.py` - 핵심 모듈 임포트 검증
- `scripts/perf_smoke.py` - 수동 성능 스모크 테스트

### 코어 모듈 (`src/core/`)
- `hwp_handler.py` - HWP 파일 조작, 보안/메타데이터/액션 실행 기반
- `action_runner.py` - 범용 `run_action` / `execute_action` 실행 및 프리셋
- `hyperlink_checker.py` - 링크 검사와 `LinkInfo` 결과 타입 정의
- `template_store.py`, `macro_recorder.py` - 템플릿/매크로 저장소
- `doc_diff.py`, `smart_toc.py` - 비교/목차 생성
- `watermark_manager.py`, `header_footer_manager.py`, `bookmark_manager.py`, `image_extractor.py`

### UI 모듈 (`src/ui/`)
- `main_window.py` - 페이지 lazy-loading, 사이드바/스택 구성
- `pages/` - 기능별 페이지 구현
- `widgets/` - 재사용 가능한 공통 위젯

### 유틸리티 (`src/utils/`)
- `worker.py` - 백그라운드 작업과 결과 집계
- `output_paths.py` - 출력 경로/충돌 회피 정책
- `filename_sanitizer.py` - 안전한 파일명 생성
- `qss_renderer.py` - 테마 토큰 기반 QSS 생성
- `com_init.py` - COM 초기화 보조
- `version.py`, `settings.py`, `theme_manager.py`, `logger.py`, `history_manager.py`

---

## ⚠️ 개발 규칙

### 필수 사항
1. 모든 함수와 핵심 멤버에 타입 힌트를 적용합니다.
2. Qt Optional 객체는 명시적으로 좁혀서 다룹니다.
3. 워커 결과 타입은 UI까지 동일한 구조로 전달합니다.
4. 저장 경로와 충돌 회피 로직은 공통 유틸리티를 재사용합니다.
5. 로그, 오류 메시지, docstring은 UTF-8 한국어 기준으로 정리합니다.

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
python scripts/verify_core_modules.py
python scripts/perf_smoke.py
```

---

## 📝 새 기능 추가 시

1. `src/core/`에 비즈니스 로직을 추가합니다.
2. 필요하면 `src/core/__init__.py` export를 갱신합니다.
3. `src/ui/pages/`에 대응 페이지를 추가합니다.
4. `src/ui/pages/__init__.py` lazy export와 `main_window.py` 페이지 로딩을 갱신합니다.
5. 워커가 필요하면 `src/utils/worker.py` 패턴을 재사용합니다.
6. `pyright .`와 `pytest -q`를 통과시킨 뒤 문서를 업데이트합니다.

---

## 🧪 현재 검증 기준 (2026-03-10)

- `pyright .` => `0 errors, 0 warnings`
- `pytest -q` => `72 passed, 2 skipped`
- 인코딩 정리 완료:
  - `src/utils/worker.py`
  - `src/core/hwp_handler.py`
- 최신 정합성 반영:
  - `ActionRunner` handler 타입을 `Protocol` 기반으로 정리
  - 링크 검사 결과 타입을 `(filename, LinkInfo)`로 고정
  - `QApplication.instance()`와 Qt 레이아웃 접근의 Optional 추론 문제 해소

---

## 📌 운영 메모

- 전역 상태는 원칙적으로 지양하지만, 매크로 녹화는 `Action Console`과 `Macro Page` 간 세션 공유를 위해 예외적으로 공유 상태를 사용합니다.
- 편집성 기능은 기본적으로 **원본 보존(새 파일 저장)** 정책을 따릅니다.
- EXE 빌드는 `hwp_master.spec` 기준이며 결과물은 `dist/` 아래에 생성됩니다.

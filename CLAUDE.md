# CLAUDE.md - HWP Master 개발 가이드

## 📋 프로젝트 개요

**HWP Master**는 pyhwpx 기반 경량 HWP 업무 자동화 도구입니다.

### 핵심 원칙
- **경량화**: Pandas/NumPy 없이 `openpyxl` 중심으로 유지
- **명시적 타입**: Pylance/Pyright에서 추론이 흔들리는 구간은 구체 타입으로 좁혀서 작성
- **운영 안정성**: 기본 저장 정책은 원본 보존, 예외 메시지와 로그는 한국어 기준으로 일관성 유지

---

## 🧱 런타임 / 품질 기준

- Python: **3.10+**
- GUI: `PySide6>=6.6.0`
- 정적 분석: `pyright .` 기준 **0 errors / 0 warnings**
- 회귀 테스트: `pytest -q` 기준 **89 passed, 2 skipped**
- 인코딩 규칙: `.editorconfig` 기준 `utf-8`, `lf`

---

## 📂 프로젝트 구조

```text
HwpMaster/
├── .editorconfig
├── pyrightconfig.json
├── LICENSE
├── PROJECT_AUDIT_PYHWPX.md
├── main.py
├── hwp_master.spec
├── scripts/
│   ├── verify_core_modules.py
│   └── perf_smoke.py
├── assets/styles/
│   ├── style.template.qss
│   └── style.qss
├── src/
│   ├── core/
│   ├── ui/
│   │   ├── main_window/
│   │   ├── pages/
│   │   └── widgets/
│   └── utils/
│       ├── atomic_write.py
│       ├── com_init.py
│       ├── history_manager.py
│       ├── output_paths.py
│       ├── qss_renderer.py
│       ├── task_tracking.py
│       ├── version.py
│       └── worker/
└── tests/
```

---

## 🎯 구현 규칙

### 타입 / Pylance
- 모든 공개 함수와 핵심 내부 함수에 타입 힌트를 작성합니다.
- Qt 객체는 `layout()` 체인이나 `QApplication.instance()` 반환값을 바로 쓰지 말고 지역 변수나 헬퍼로 구체 타입을 좁힙니다.
- `object`나 느슨한 tuple 흐름이 생기지 않도록 워커 결과 타입은 끝까지 동일하게 유지합니다.
- 테스트 더블이 필요한 실행기 계층은 concrete 클래스보다 `Protocol`을 우선합니다.

### 파일 / 경로
- 하드코딩된 문자열 경로 대신 `Path`를 사용합니다.
- 출력 경로 정책은 `src/utils/output_paths.py`로 통일합니다.
- 파일명 정리는 `src/utils/filename_sanitizer.py`를 우선 사용합니다.
- 설정/히스토리/템플릿/매크로 메타데이터 저장은 `src/utils/atomic_write.py` 헬퍼를 우선 사용합니다.

### UI / 워커
- 새 기능은 `src/core/`와 `src/ui/pages/`를 함께 추가하고, 메인 윈도우 lazy-loading 경로까지 연결합니다.
- 백그라운드 작업은 `src/utils/worker/` 패턴을 따르고, 성공/실패 판정은 결과 집계와 동일한 기준으로 맞춥니다.
- 작업 완료 후 최근 파일과 홈 대시보드 히스토리 갱신은 `src/utils/task_tracking.py` 헬퍼로 통일합니다.

---

## ⚠️ 금지 사항

1. Pandas/NumPy 추가
2. 근거 없는 `Any` 확산
3. 하드코딩된 절대 경로
4. TODO/FIXME 주석 방치
5. 깨진 한글 문자열이나 비 UTF-8 텍스트 커밋

---

## 🔧 자주 쓰는 명령어

```bash
pip install -r requirements.txt
python main.py
pyright .
pytest -q
python scripts/verify_core_modules.py
python scripts/perf_smoke.py
```

---

## 📝 변경 체크리스트

- [ ] 타입 힌트와 docstring을 추가했다.
- [ ] `pyright .`가 깨지지 않는다.
- [ ] `pytest -q`가 기존 기준을 유지한다.
- [ ] 새 페이지/모듈이면 `__init__.py`와 `src/ui/main_window/` 연결을 반영했다.
- [ ] 로그/오류 메시지/주석의 한국어 표현을 통일했다.

---

## 📌 운영 정합성 메모 (2026-03-25)

- 최신 기준:
  - `pyright .` => `0 errors, 0 warnings`
  - `pytest -q` => `89 passed, 2 skipped`
- 최근 반영:
  - `atomic_write.py` 추가 후 settings/history/action-template/template-store/macro 저장 경로를 원자적 쓰기로 통일
  - `task_tracking.py` 추가 후 최근 파일/작업 히스토리 기록 로직을 공통화
  - 홈 페이지에 최근 작업/즐겨찾기 패널을 배치하고 메인 윈도우 설정 인스턴스와 연결
  - 템플릿 출력 확장자 정책을 원본 템플릿 suffix와 일치하도록 강제
  - Smart TOC HTML 출력의 escape/page-number 표시와 style-hint 정렬 통계를 보강
  - `pyrightconfig.json`, `.editorconfig` 추가
  - `worker/`, `hwp_handler/` 한글 인코딩/문구 복구
  - `ActionRunner` handler 타입을 `Protocol` 기반으로 정리
  - 링크 검사 결과 타입을 `(filename, LinkInfo)`로 고정
  - `tests/test_repository_text_integrity.py`로 UTF-8 및 모지바케 회귀 감시 추가
  - same-path package facade 리팩토링과 `tests/test_same_path_package_facades.py` 추가
- 전역 상태 원칙 예외:
  - 전역 상태는 지양하되, 매크로 녹화는 `Action Console`과 `Macro Page` 간 세션 공유를 위해
    `MacroRecorder`의 공유 녹화 상태를 사용함
- 저장 정책 기본값:
  - 신규/편집성 기능은 기본적으로 **원본 보존(새 파일 저장)**이며, 덮어쓰기는 명시 선택 시에만 허용

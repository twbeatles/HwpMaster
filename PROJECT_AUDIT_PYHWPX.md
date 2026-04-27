# HWP Master pyhwpx 확장 프로젝트 감사 보고서

작성일: 2026-02-25  
최종 업데이트: 2026-04-27
기준 환경: Windows + 한글(HWP) 설치 환경, `pyhwpx 1.6.6`, rhwp `0.7.6`

## 1. 문서 목적

- pyhwpx 기반 자동화와 rhwp 기반 내장 편집기 확장 범위, 현재 저장소 구조를 한 번에 점검한다.
- 감사 이후 반영된 수정 사항과 아직 운영상 주의가 필요한 항목을 정리한다.
- 최신 품질 기준인 `pyright .`, `pytest -q`, UTF-8 텍스트 무결성 상태를 기록한다.

## 2. 현재 구조 요약

| 영역 | 핵심 파일 | 역할 |
|---|---|---|
| 앱 진입 / 패키징 | `main.py`, `hwp_master.spec` | 앱 시작, 스타일 초기화, PyInstaller 배포 설정 |
| Core | `src/core/hwp_handler/`, `action_runner/`, `capability_mapper.py`, `editor/` | HWP 제어, 범용 액션 실행, pyhwpx 기능 매핑, rhwp 편집 세션/저장/API 서버 |
| UI | `src/ui/main_window/`, `src/ui/pages/*` | 기능별 페이지 lazy-loading, 대시보드/설정/고급 콘솔/문서 편집 |
| rhwp runtime | `assets/rhwp_studio/`, `vendor/rhwp/` | self-hosted 편집 UI, WASM 런타임, upstream 라이선스/기준 보관 |
| Worker / Utils | `src/utils/worker/`, `output_paths.py`, `atomic_write.py`, `task_tracking.py` | 백그라운드 실행, 저장 정책, 원자적 저장, 최근 작업 추적 |
| 품질 / 문서 | `tests/*`, `README.md`, `CLAUDE.md`, `GEMINI.md`, `FUNCTIONAL_IMPLEMENTATION_AUDIT_2026-04-19.md` | 회귀 테스트, 개발 가이드, 운영 메모 |

## 3. 감사 결과 반영 현황

### 완료된 항목

- Phase 0 즉시 결함 수정
  - 매크로 프리셋 저장/재생 흐름 정리
  - README 설명과 실제 구현의 불일치 수정
  - 설정값 반영 누락 보완
- Phase 1 문서 보안/개인정보 처리 보강
  - 메타데이터 정리, 개인정보 스캔, 비밀번호 적용 경로 추가
- Phase 2 데이터 주입/필드/메일 머지 보강
  - 필드 목록/채우기, 메타 태그 처리, 파일명 템플릿, 메일 머지 흐름 정리
- Phase 3 범용 액션 확장
  - `ActionRunner`와 `CapabilityMapper` 추가
  - `Action Console`에서 `run_action` / `execute_action` 흐름 제공
- 2026-02-27 ~ 2026-02-28 감사 후속 수정
  - 원본 보존 기본 저장 정책 정리
  - remove 모드 출력 충돌 회피
  - 링크 리포트 저장 실패 반영
  - Worker 성공/실패 판정 보정
  - 매크로 ID 충돌 방지
- 2026-03-15 정합성 마감
  - `pyright .` 기준 `0 errors, 0 warnings`
  - `worker/`, `hwp_handler/` 한글 문자열과 주석의 UTF-8 정리
  - `tests/test_repository_text_integrity.py` 추가
  - README/감사 문서/`.spec`/워크스페이스 설정 동기화
- 2026-03-18 구조 분할 리팩토링
  - 같은 import 경로 유지형 패키지 전환: `hwp_handler`, `action_runner`, `doc_diff`, `template_store`, `macro_recorder`, `worker`, `main_window`
  - 루트 파사드 + 내부 책임 모듈 구조로 분리
  - import/monkeypatch 호환 회귀 테스트 추가
- 2026-03-25 저장/대시보드 후속 정리
  - `atomic_write.py`를 도입해 settings/history/action-template/template-store/macro 저장 경로를 원자적 쓰기로 통일
  - `task_tracking.py`를 도입해 최근 파일/작업 히스토리 기록을 공통화
  - 홈 대시보드에 최근 작업/즐겨찾기 패널을 추가하고 같은 config dir 기준 히스토리를 재사용
  - 템플릿 생성 시 출력 확장자를 원본 템플릿 suffix와 일치시키고, 필드 입력이 있는 경우 별도 입력 다이얼로그로 생성
  - Smart TOC HTML escape/page-number 표기와 style-hint 정렬 통계를 보강
 - 2026-04-19 기능 구현 감사 후속 반영
   - `CapabilityMapper` fallback 복구, repo-local `pyhwpx` stub, `pyrightconfig.json` 정리
   - `TemplateStoreError` 도입과 템플릿 페이지 예외 처리 통일
   - 하이퍼링크 스캔과 리포트 저장 분리, 취소 이력 상태 기록, 홈 대시보드 상태 배지 추가
   - 설정 페이지 환경 진단 워커/UI 추가
   - opt-in 실문서 smoke 테스트를 `convert/merge/split/metadata/watermark/header_footer/bookmark/hyperlink` 범위로 확장
   - `hwp_master.spec`에 최신 기능 감사 문서를 조건부 번들링하도록 정리
- 2026-04-27 rhwp 내장 편집기 대개편 1차
  - rhwp `0.7.6` npm 산출물을 `vendor/rhwp/`에 보관하고, 실행용 JS/WASM을 `assets/rhwp_studio/`로 번들링
  - `src/core/editor/` 패키지를 추가해 `EditorSession`, `EditorSaveService`, `EditorAssetServer` 책임을 분리
  - `src/ui/pages/editor_page.py`를 추가하고 홈/사이드바/main_window lazy-loading 경로에 `문서 편집` 워크스페이스 연결
  - Python localhost API로 문서 바이트 제공, 저장, 상태 갱신을 처리하고 token 검증을 적용
  - HWP 저장 전 최초 백업, HWPX 직접 덮어쓰기 보호, 복구본 저장 정책 구현
  - `hwp_master.spec`에 QtWebEngine/QtWebChannel hidden import와 rhwp asset/license 번들링 반영

### 남아 있는 운영상 주의점

- 실제 HWP COM 동작은 Windows + 한글 설치 환경 의존성이 있다.
- 일부 pyhwpx 세부 동작은 버전별 차이가 있어 best-effort 경로가 남아 있다.
- rhwp 기반 HWPX 직접 덮어쓰기는 round-trip 검증 전까지 보호 모드로 제한한다.
- 내장 편집기의 고급 편집 기능(쪽 설정, 개체, 필드 등)은 rhwp API 위에 단계적으로 UI를 확장해야 한다.
- PyInstaller EXE 빌드는 `.spec` 변경 시 주기적 실기기 스모크 테스트가 필요하다.

## 4. pyhwpx/rhwp 활용 전략

- 자주 쓰는 업무 자동화는 전용 UI 페이지와 Worker로 안정화한다.
- pyhwpx 전체 API를 전부 감싸기보다, 공통 경로는 `HwpHandler`와 `ActionRunner`로 재사용한다.
- 전용 UI가 아직 없는 기능은 `Action Console`과 capability snapshot으로 확장 여지를 확보한다.
- 문서 편집은 rhwp WebAssembly 런타임을 QtWebEngine에 self-host하고, 저장/백업/복구 정책은 Python `EditorSaveService`에서 통제한다.
- 한컴 의존 자동화 기능은 유지하되, rhwp로 검증된 편집/렌더링 기능부터 독립 경로를 확장한다.
- 커버리지 드리프트는 테스트와 문서로 관리하고, 실제 사용자 기능은 저장 정책과 오류 메시지 일관성을 우선한다.

## 5. 최신 검증 기준

```bash
pyright .
pytest -q
python -X utf8 - <<'PY'
from pathlib import Path
for path in [Path("main.py"), Path("src/core/hwp_handler/__init__.py"), Path("src/utils/worker/__init__.py")]:
    path.read_text(encoding="utf-8")
print("UTF-8 OK")
PY
```

- 정적 분석: `0 errors, 0 warnings`
- 회귀 테스트: `106 passed, 6 skipped`
- opt-in 실문서 smoke: 현재 런타임 기준 skip 가능
- 텍스트 무결성: `tests/test_repository_text_integrity.py` 통과
- 편집기 코어: `tests/test_editor_core.py`에서 저장/백업/복구/API token 검증
- PyInstaller 빌드: `pyinstaller hwp_master.spec --noconfirm` 통과

## 6. 권장 후속 조치

- 배포 후보마다 `pyinstaller hwp_master.spec` 실빌드와 실행 스모크 테스트를 수행한다.
- rhwp runtime 갱신 시 `vendor/rhwp/README.md`, `assets/rhwp_studio/rhwp-core/`, `hwp_master.spec`의 라이선스/번들링 정합성을 함께 갱신한다.
- Windows + 한글 설치 환경에서 실문서 기반 smoke test를 주기적으로 돌린다.
- 테스트 기준선이나 저장 정책이 바뀌면 README와 핵심 운영 문서를 같은 커밋에서 함께 갱신한다.
- 홈 대시보드의 최근 작업/즐겨찾기 UX는 설정/히스토리 파일 포맷 변경과 함께 검증한다.

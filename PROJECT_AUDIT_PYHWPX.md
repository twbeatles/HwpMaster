# HWP Master pyhwpx 확장 프로젝트 감사 보고서

작성일: 2026-02-25  
최종 업데이트: 2026-03-15  
기준 환경: Windows + 한글(HWP) 설치 환경, `pyhwpx 1.6.6`

## 1. 문서 목적

- pyhwpx 기반 기능 확장 범위와 현재 저장소 구조를 한 번에 점검한다.
- 감사 이후 반영된 수정 사항과 아직 운영상 주의가 필요한 항목을 정리한다.
- 최신 품질 기준인 `pyright .`, `pytest -q`, UTF-8 텍스트 무결성 상태를 기록한다.

## 2. 현재 구조 요약

| 영역 | 핵심 파일 | 역할 |
|---|---|---|
| 앱 진입 / 패키징 | `main.py`, `hwp_master.spec` | 앱 시작, 스타일 초기화, PyInstaller 배포 설정 |
| Core | `src/core/hwp_handler.py`, `action_runner.py`, `capability_mapper.py` | HWP 제어, 범용 액션 실행, pyhwpx 기능 매핑 |
| UI | `src/ui/main_window.py`, `src/ui/pages/*` | 기능별 페이지 lazy-loading, 대시보드/설정/고급 콘솔 |
| Worker / Utils | `src/utils/worker.py`, `output_paths.py`, `filename_sanitizer.py` | 백그라운드 실행, 저장 정책, 충돌 회피 |
| 품질 / 문서 | `tests/*`, `README.md`, `CLAUDE.md`, `GEMINI.md` | 회귀 테스트, 개발 가이드, 운영 메모 |

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
  - `worker.py`, `hwp_handler.py` 한글 문자열과 주석의 UTF-8 정리
  - `tests/test_repository_text_integrity.py` 추가
  - README/감사 문서/`.spec`/워크스페이스 설정 동기화

### 남아 있는 운영상 주의점

- 실제 HWP COM 동작은 Windows + 한글 설치 환경 의존성이 있다.
- 일부 pyhwpx 세부 동작은 버전별 차이가 있어 best-effort 경로가 남아 있다.
- PyInstaller EXE 빌드는 `.spec` 변경 시 주기적 실기기 스모크 테스트가 필요하다.

## 4. pyhwpx 활용 전략

- 자주 쓰는 업무 자동화는 전용 UI 페이지와 Worker로 안정화한다.
- pyhwpx 전체 API를 전부 감싸기보다, 공통 경로는 `HwpHandler`와 `ActionRunner`로 재사용한다.
- 전용 UI가 아직 없는 기능은 `Action Console`과 capability snapshot으로 확장 여지를 확보한다.
- 커버리지 드리프트는 테스트와 문서로 관리하고, 실제 사용자 기능은 저장 정책과 오류 메시지 일관성을 우선한다.

## 5. 최신 검증 기준

```bash
pyright .
pytest -q
python -X utf8 - <<'PY'
from pathlib import Path
for path in [Path("main.py"), Path("src/core/hwp_handler.py"), Path("src/utils/worker.py")]:
    path.read_text(encoding="utf-8")
print("UTF-8 OK")
PY
```

- 정적 분석: `0 errors, 0 warnings`
- 회귀 테스트: `67 passed, 2 skipped`
- 텍스트 무결성: `tests/test_repository_text_integrity.py` 통과

## 6. 권장 후속 조치

- 배포 후보마다 `pyinstaller hwp_master.spec` 실빌드와 실행 스모크 테스트를 수행한다.
- Windows + 한글 설치 환경에서 실문서 기반 smoke test를 주기적으로 돌린다.
- 테스트 기준선이나 저장 정책이 바뀌면 README와 두 감사 문서를 같은 커밋에서 함께 갱신한다.

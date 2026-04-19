# HWP Master 기능 구현 감사 후속 반영 기록

작성일: 2026-04-19  
기준 문서: `README.md`, `CLAUDE.md`, `GEMINI.md`, `PROJECT_AUDIT_PYHWPX.md`  
목적: 2026-04-19 기능 감사 항목의 실제 반영 여부와 최신 저장소 기준을 한 문서에서 추적

## 1. 반영 범위

- `CapabilityMapper` fallback 복구
- repo-local `pyhwpx` stub + `pyrightconfig.json` 정리
- 템플릿 저장소/페이지 예외 처리 안정화
- 하이퍼링크 검사와 리포트 저장 분리
- 취소 작업 이력 기록 + 홈 대시보드 상태 배지
- 설정 페이지 `환경 진단` 워커/UI 추가
- opt-in 실문서 smoke 테스트 확대
- `.spec` 및 주요 Markdown 문서 정합성 점검

## 2. 구현 완료 항목

### 품질 게이트 복구

- `src/core/capability_mapper.py`
  - `CapabilitySnapshot.categories`를 기본 총계로 사용하도록 보정
  - pyhwpx 비가용 환경에서도 카테고리 totals가 유지되도록 수정
- `typings/pyhwpx/__init__.pyi`
  - `Hwp`, `HAction`, `HParameterSet`, `HeadCtrl` 중심의 느슨한 stub 추가
- `pyrightconfig.json`
  - `stubPath: "typings"` 설정
- `src/ui/main_window/operations.py`
  - `OptionalMemberAccess` 발생 구간을 지역 변수 + `None` 체크로 정리

### 템플릿 저장소/페이지 안정화

- `src/core/template_store/models.py`
  - `TemplateStoreError` 추가
- `src/core/template_store/service.py`
  - 파일 복사/삭제 계열 실패를 raw `OSError` 대신 `TemplateStoreError`로 래핑
- `src/ui/pages/template_page.py`
  - 내장 템플릿 등록, 사용자 템플릿 추가, 삭제, 생성 플로우를 모두 메시지 박스로 수렴

### 하이퍼링크 검사 재설계

- `src/ui/pages/hyperlink_page.py`
  - 일반 스캔에서는 임시 HTML 리포트를 만들지 않도록 변경
  - `_on_error()`에서 버튼/프로그레스 상태를 복구하도록 수정
  - Export 버튼은 사용자가 실제로 결과를 저장할 때만 동작
- `src/utils/worker/editing.py`
  - 명시적 `output_dir`가 있을 때만 리포트 저장 경로를 타도록 기존 정책을 유지
  - 일반 UI 스캔에서는 `output_dir=""`로 메모리 결과만 사용

### 취소 이력 기록 + 대시보드 표시

- `src/utils/history_manager.py`
  - `HistoryItem.status` persisted 필드 추가
  - `completed | partial | failed | cancelled` 상태 규칙 구현
- `src/utils/task_tracking.py`
  - 취소 작업도 이력에 저장하되 recent files는 갱신하지 않도록 수정
- `src/ui/widgets/history_panel.py`
  - 상태 배지와 색상 표시 추가

### 설정 페이지 환경 진단

- `src/utils/worker/analysis.py`
  - `EnvironmentDiagnosisWorker` 추가
  - 진단 항목: `pyhwpx import`, `COM 초기화`, `HWP 기동/종료`, `기본 출력 폴더 쓰기 테스트`
- `src/ui/pages/settings_page.py`
  - 시스템 섹션에 `환경 진단` 버튼, 요약 라벨, 상세 결과 영역 추가

### 실문서 통합 테스트 확대

- `tests/test_real_hwp_feature_smoke.py`
  - `HWPMASTER_REAL_DOC_TESTS=1` 게이트 유지
  - 변환, 병합/분할, 메타정보 정리, 워터마크, 헤더/푸터, 북마크, 하이퍼링크 export smoke 추가
- 개별 런타임에서 북마크/하이퍼링크 삽입이 지원되지 않으면 해당 테스트만 `skip` 처리

## 3. 문서 / 패키징 정합성 점검

### `.spec` 점검 결과

- `hwp_master.spec`는 런타임 동작 관점에서 즉시 수정이 필요한 문제는 발견되지 않았습니다.
- 이번 반영으로 아래만 보강했습니다.
  - `FUNCTIONAL_IMPLEMENTATION_AUDIT_2026-04-19.md`를 조건부 번들 문서 목록에 추가
  - `typings/pyhwpx`는 개발용 정적 분석 자산이므로 EXE 번들 대상이 아님을 주석으로 명시

### Markdown 정합성 반영

- `README.md`
  - 2026-04-19 업데이트, 환경 진단, 최신 테스트 기준, 새 감사 문서 링크 반영
- `CLAUDE.md`
  - 최신 품질 기준, 기능 감사 문서 경로, 패키징 메모 보강
- `GEMINI.md`
  - 2026-04-19 기준 검증 수치와 최신 운영 메모 반영
- `PROJECT_AUDIT_PYHWPX.md`
  - 최신 감사 문서 참조와 `.spec` 정합성 반영

## 4. 검증 결과

```text
pyright .
=> 0 errors, 0 warnings

pytest -q
=> 100 passed, 6 skipped

HWPMASTER_REAL_DOC_TESTS=1 pytest -q tests/test_real_hwp_doc_diff_smart_toc.py tests/test_real_hwp_feature_smoke.py
=> 현재 런타임 6 skipped
```

## 5. 결론

- 2026-04-19 감사 계획 범위는 저장소 기준으로 반영 완료 상태입니다.
- 현재 남은 리스크는 주로 실제 Windows + 한글 + pyhwpx 런타임 의존성입니다.
- 배포 직전에는 `pyinstaller hwp_master.spec` 실빌드와 실기기 smoke를 한 번 더 수행하는 편이 안전합니다.

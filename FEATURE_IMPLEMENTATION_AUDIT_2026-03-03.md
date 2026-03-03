# HWP Master 기능 구현 점검 보고서 (2026-03-03)

## 점검 기준
- 참조 문서: `README.md`, `CLAUDE.md`
- 실행 검증: `pytest -q` 결과 `72 passed, 2 skipped` 확인
- 점검 관점: 기능 정확성, 저장 정책(원본 보존), 충돌/유실 위험, 테스트 공백

## 핵심 이슈 반영 상태

### 1. [Implemented][High] Header/Footer, Watermark Worker 성공 판정 오류
- 근거 코드:
  - `src/utils/worker.py:1093` (`HeaderFooterWorker` 결과를 `success=True`로 고정)
  - `src/utils/worker.py:1177` (`WatermarkWorker` 결과를 `success=True`로 고정)
- 문제:
  - 내부 `fail_count`가 1 이상이어도 최종 결과가 성공으로 반환됩니다.
  - UI에서 실패 일부가 있어도 성공 토스트/완료로 보일 수 있습니다.
- 영향:
  - 운영자가 실패를 놓치고 후속 작업(배포, 보고)에 잘못된 결과를 사용할 수 있습니다.
- 적용 내용:
  - `success=(fail_count == 0)`로 수정.
  - 실패 파일 요약(`최대 3건 + N more`)을 `error_message`로 전달하도록 반영.

### 2. [Implemented][High] Header/Footer, Watermark 제거 모드에서 파일명 충돌 시 덮어쓰기 위험
- 근거 코드:
  - `src/utils/worker.py:1085-1086`
  - `src/utils/worker.py:1169-1170`
- 문제:
  - 제거(remove) 모드에서 출력 경로를 `output_dir + 원본파일명`으로 직접 결합합니다.
  - 서로 다른 폴더의 동명 파일을 동시에 처리하면 뒤에 처리된 파일이 앞 결과를 덮어쓸 수 있습니다.
- 영향:
  - 결과 파일 유실/혼선.
- 적용 내용:
  - remove 모드 출력 경로 생성을 `resolve_output_path(...)` 기반으로 통일.

### 3. [Implemented][High] 이미지 추출 시 다중 문서 출력 충돌 가능 (동일 stem/재실행)
- 근거 코드:
  - `src/utils/worker.py:756` (`ImageExtractWorker`가 파일별 분리 없이 `extract_images(...)` 호출)
  - `src/core/image_extractor.py:177-181` (고정 규칙 `source_stem_001.ext`로 저장)
- 문제:
  - 여러 입력 파일이 같은 파일명 stem(예: `report.hwp`)일 때 같은 출력 폴더로 저장되면 이미지명이 충돌합니다.
  - 같은 작업을 같은 폴더에 재실행해도 기존 이미지가 덮어써질 수 있습니다.
- 영향:
  - 이미지 유실, 원본-결과 매핑 불가.
- 적용 내용:
  - `ImageExtractWorker`가 `extract_images(...)` 직접 호출 대신 `batch_extract(...)`를 사용.
  - 파일별 하위폴더 정책을 기본 경로로 고정하고, 동명 폴더 충돌 시 suffix(`_1`, `_2` ...) 유지.
  - `batch_extract(..., prefix=\"\")` 인자 추가 후 내부 전달.

### 4. [Implemented][Medium] DocDiff 텍스트 추출 fallback 임시파일 정리 누락 가능
- 근거 코드:
  - `src/core/doc_diff.py:253` (`NamedTemporaryFile(..., delete=False)`)
  - `src/core/doc_diff.py:256` (`hwp.save_as(tmp_path, format="TEXT")`)
  - `src/core/doc_diff.py:261` (`Path(tmp_path).unlink(...)`가 정상 경로에서만 실행)
- 문제:
  - `save_as` 또는 파일 읽기 중 예외가 발생하면 `unlink`가 실행되지 않아 임시 파일이 남을 수 있습니다.
- 영향:
  - 디스크 누수, 민감 텍스트 잔존 위험.
- 적용 내용:
  - fallback 경로를 `try/finally`로 감싸 예외 발생 시에도 임시파일 삭제를 보장.

### 5. [Implemented][Medium] 매크로 ID 생성 단위(초)로 인한 저장 충돌 가능
- 근거 코드:
  - `src/core/macro_recorder.py:320` (ID: `YYYYMMDDHHMMSS`)
  - `src/core/macro_recorder.py:329` (동일 key 덮어쓰기)
  - `src/core/macro_recorder.py:333` (스크립트 파일명도 동일 ID 기반)
- 문제:
  - 같은 초에 매크로를 2개 저장하면 ID/파일명이 충돌하여 기존 매크로가 덮어써질 수 있습니다.
- 영향:
  - 사용자 매크로 유실.
- 적용 내용:
  - `_generate_unique_macro_id()`를 추가하고 `macro_YYYYmmddHHMMSSffffff` 형식으로 생성.
  - `_macros`/스크립트 파일 충돌 시 재생성, 최종 fallback UUID suffix를 적용.

## 테스트 보강 (추가 완료)
- 추가된 테스트:
  - `tests/test_header_footer_worker_result_policy.py`
  - `tests/test_watermark_worker_result_policy.py`
  - `tests/test_remove_mode_output_collision.py`
  - `tests/test_image_extractor_output_collision.py`
  - `tests/test_doc_diff_tempfile_cleanup.py`
  - `tests/test_macro_recorder_id_uniqueness.py`
- 검증 범위:
  - Worker 부분 실패 시 `result.success`/요약 메시지 정합성
  - remove 모드 출력 충돌 회피
  - 이미지 추출 파일별 하위폴더 및 `prefix` 전달
  - DocDiff fallback 임시파일 정리 보장
  - 매크로 ID 충돌 회피

## 추가 구현 권장 (기능 보강)
- 저장 정책 통일:
  - 편집성 기능 전체에 `save_mode`(`none/new/overwrite`)를 공통 적용해 UX/정책 일관화.
- 결과 추적성 강화:
  - 배치 작업마다 `manifest.json`(입력-출력-실패원인)을 남겨 감사/재처리 용이성 확보.
- 안전장치:
  - 덮어쓰기 선택 시 자동 백업 옵션(예: `_backup_YYYYmmdd_HHMMSS`) 제공.

## 문서/빌드 정합성 보강 (추가 반영)
- `hwp_master.spec`
  - 누락 파일로 빌드 실패할 수 있던 고정 데이터 항목(`FEATURE_IMPLEMENTATION_AUDIT_2026-02-27.md`) 제거.
  - 문서 번들 대상을 존재 파일 기준으로 동적 추가하도록 변경:
    - `README.md`, `PROJECT_AUDIT_PYHWPX.md`, `FEATURE_IMPLEMENTATION_AUDIT_2026-03-03.md`, `CLAUDE.md`, `GEMINI.md`
- `README.md`
  - 문서 링크를 현재 파일명(`FEATURE_IMPLEMENTATION_AUDIT_2026-03-03.md`)으로 수정.
- `CLAUDE.md`, `GEMINI.md`, `PROJECT_AUDIT_PYHWPX.md`
  - 2026-03-03 운영 정합성 메모를 추가하고 최신 회귀 기준(`72 passed, 2 skipped`) 반영.
- `.gitignore`
  - 정적분석/타입체크 캐시 및 일반 임시 파일 무시 항목 보강:
    - `.mypy_cache/`, `.ruff_cache/`, `.pyre/`, `*.tmp`, `*.bak`

## 결론
- 계획한 핵심 이슈 5건(High 3, Medium 2)을 코드/테스트/문서까지 일괄 반영했습니다.
- 이번 사이클에서 제외한 항목은 초기 계획대로 `save_mode 공통화`, `manifest`, `자동 백업`입니다.

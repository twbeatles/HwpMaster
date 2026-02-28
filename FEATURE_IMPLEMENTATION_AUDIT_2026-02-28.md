# 기능 구현 감사 보고서 (2026-02-28)

기준 문서: `CLAUDE.md`, `README.md`  
점검 방식: 코드 정적 리뷰 + 단위 테스트 실행 + 재현 스크립트 확인

## 1. 실행/점검 요약
- 테스트 실행: `pytest -q`
- 결과: `65 passed, 2 skipped` (2026-02-28 기준)
- 결론: 섹션 2의 핵심 이슈(충돌/성공 판정/데이터 누락/리포트 저장 실패/문서 링크)는 반영 완료.  
  섹션 3 구조 개선안(저장 정책 공통화, 결과 스키마 표준화, dry-run)은 차기 범위로 유지.

## 2. 잠재 이슈 (우선순위 순)
아래 항목은 감사 시점에 식별된 이슈이며, 반영 결과는 섹션 5에 정리함.

### [High] 매크로 저장 ID 충돌로 기존 매크로가 덮어써짐
- 근거:
  - `src/core/macro_recorder.py:320`
  - ID 생성이 초 단위 타임스탬프(`macro_%Y%m%d%H%M%S`) 1개 경로만 사용
- 재현 확인:
  - 동일 초 내 `save_macro()` 2회 호출 시 ID가 동일하게 생성됨
  - 결과적으로 `_macros` 딕셔너리와 `.py` 스크립트 파일이 마지막 매크로로 덮어써짐
- 영향:
  - 사용자 매크로 유실(데이터 손실)
- 권장 조치:
  - ID를 `uuid4` 또는 `timestamp + random/monotonic` 조합으로 변경
  - 회귀 테스트 추가: 빠른 연속 저장 시 ID 유니크 보장

### [High] Header/Footer, Watermark Worker가 실패가 있어도 성공으로 반환
- 근거:
  - `src/utils/worker.py:1093`
  - `src/utils/worker.py:1177`
  - 두 지점 모두 `WorkerResult(success=True, ...)` 고정 반환
- 재현 확인:
  - 성공 1건/실패 1건을 리턴하는 fake manager로 실행 시 `result.success == True`로 반환됨
- 영향:
  - UI에서 실패가 있어도 완료 성공으로 오인될 수 있음
- 권장 조치:
  - `success=(fail_count == 0)`로 변경
  - `error_message`에 실패 요약(최대 N건) 포함
  - 회귀 테스트 추가: partial failure 시 `success=False` 검증

### [Medium] remove 모드 출력 경로 충돌 시 파일 덮어쓰기 가능
- 근거:
  - `src/utils/worker.py:1085`
  - `src/utils/worker.py:1169`
  - `Path(output_dir) / Path(file_path).name` 직접 결합 (충돌 회피 없음)
- 재현 확인:
  - `C:/a/report.hwp`, `D:/b/report.hwp` 두 파일을 같은 출력 폴더로 처리하면 둘 다 `.../report.hwp`로 저장
- 영향:
  - 결과 파일 일부가 사라지는 silent overwrite 위험
- 권장 조치:
  - `resolve_output_path()` 사용으로 충돌 회피
  - 필요 시 접미사(`_removed`, `_cleaned`) 정책 통일

### [Medium] Excel에서 첫 컬럼이 비어 있으면 유효 행도 스킵됨
- 근거:
  - `src/core/excel_handler.py:113-115`
  - `src/core/excel_handler.py:201-203`
  - 첫 셀만 기준으로 빈 행 판정
- 재현 확인:
  - 행 데이터 `[None, "keep"]`가 `read_excel`, `read_excel_streaming`에서 누락됨
- 영향:
  - 데이터 주입 시 일부 대상 문서가 생성되지 않을 수 있음
- 권장 조치:
  - CSV와 동일하게 “모든 컬럼이 빈 값일 때만 스킵” 정책으로 통일
  - 회귀 테스트 추가: 첫 컬럼 빈 값 + 다른 컬럼 값 존재 케이스

### [Medium] 링크 검사 리포트 저장 실패가 실패로 집계되지 않음
- 근거:
  - `src/utils/worker.py:994-995`
  - `checker.generate_report(...)` 반환값 미검증
- 영향:
  - 실제 리포트 저장 실패가 사용자에게 정상 완료처럼 보일 수 있음
- 권장 조치:
  - `generate_report` 결과를 확인해 실패 카운트/경고에 반영
  - 아티팩트에 `report_path`, `report_saved` 명시

### [Low] 테스트 공백 (핵심 리스크 지점 미커버)
- 관찰:
  - `tests/`에 `HeaderFooterWorker`, `WatermarkWorker`, `Excel 첫컬럼 빈행 처리`에 대한 직접 테스트 부재
- 영향:
  - 회귀 시 조기 탐지 실패 가능
- 권장 조치:
  - `tests/test_header_footer_worker_policy.py`
  - `tests/test_watermark_worker_policy.py`
  - `tests/test_excel_handler_blank_first_cell.py`

### [Low] README 문서 링크 정합성 이슈
- 근거:
  - `README.md:202`에서 `FEATURE_IMPLEMENTATION_AUDIT_2026-02-27.md` 참조
  - 현재 저장소에는 해당 파일이 없음
- 영향:
  - 문서 탐색 혼선
- 권장 조치:
  - README 링크를 실제 파일명으로 갱신하거나 alias 파일 추가

## 3. 추가 구현 권장사항

1. 저장 정책 공통화
- Header/Footer, Watermark, Bookmark, Action Console에서 `none/new/overwrite`를 공통 유틸로 통일해 정책 편차를 제거.

2. 실패 요약 표준화
- 모든 Worker가 `warnings`, `artifacts`, `failed_items`를 같은 키 스키마로 반환하도록 정리.

3. 파괴적 작업의 사전 검증(dry-run)
- 북마크 삭제/덮어쓰기형 작업에 대해 “실제 반영 전 예상 변경 수”를 먼저 보여주는 옵션 추가.

## 4. 우선 조치 제안 (실행 순서)
1. `macro_recorder` ID 유니크 보장 수정 (데이터 유실 방지)
2. Header/Footer·Watermark Worker 성공 판정 수정
3. remove 모드 출력 충돌 방지 + 테스트 추가
4. Excel 빈 행 판정 정책 통일 + 테스트 추가

## 5. 2026-02-28 반영 완료 내역 (Closing)
1. 매크로 ID 충돌 해소
- `src/core/macro_recorder.py`
- `save_macro()` ID를 `macro_<uuid4hex>`로 전환, 스크립트 파일명도 동일 ID 사용

2. Header/Footer·Watermark Worker 정책 정합화
- `src/utils/worker.py`
- `success=(fail_count==0)` 적용
- remove 모드 저장 경로를 `resolve_output_path()`로 변경
- 실패 요약을 `error_message`에 포함

3. Excel 빈 행 판정 정책 통일
- `src/core/excel_handler.py`
- 첫 컬럼 기준 스킵 제거, 행 전체 빈 값(`None`/공백 문자열)일 때만 스킵

4. Hyperlink 리포트 저장 실패를 실패로 반영
- `src/utils/worker.py`
- `generate_report()` 실패 시 fail count 및 warnings 반영, 최종 실패 처리

5. 문서/배포 정합성 수정
- `README.md`: 감사 문서 링크 최신화 유지 확인
- `hwp_master.spec`: `FEATURE_IMPLEMENTATION_AUDIT_2026-02-28.md` 동봉하도록 수정

6. 신규 회귀 테스트 추가 및 통과
- `tests/test_macro_recorder_id_uniqueness.py`
- `tests/test_header_footer_worker_policy.py`
- `tests/test_watermark_worker_policy.py`
- `tests/test_excel_handler_blank_first_cell.py`
- `tests/test_hyperlink_worker_report_save_policy.py`

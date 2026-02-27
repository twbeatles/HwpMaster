# HWP Master Audit 항목 개선 완료 보고서 (2026-02-27)

## 1) 범위
- 기준 계획: `HWP Master Audit 항목 전체 개선 실행 계획`
- 기본 원칙: **원본 보존 기본**, 덮어쓰기는 명시 선택 시에만 허용
- 점검 대상: `src/core`, `src/ui/pages`, `src/utils/worker.py`, `README.md`, `hwp_master.spec`, `tests`

## 2) 최종 검증 결과
- 전체 테스트: `pytest -q`
- 결과: **`57 passed, 2 skipped`**
- 실문서/COM 의존 테스트는 기존 정책대로 조건부 skip 유지

## 3) 항목별 반영 상태

### 3.1 품질 게이트 복구 (QSS)
- 상태: ✅ 완료
- 반영:
  - `tests/test_qss_render.py`를 테마 토큰 기반 검증으로 변경
  - 다크/라이트 렌더링 핵심 토큰 검증 및 토큰 미치환 검증 적용

### 3.2 데이터 주입 안정성
- 상태: ✅ 완료
- 반영:
  - CSV 스킵 기준을 `첫 컬럼 비어있음`에서 `모든 컬럼 비어있음`으로 변경
  - 파일명 충돌 시 자동 suffix(`_1`, `_2`...) 부여
  - 결과 데이터 확장: `skipped_empty_rows`, `filename_collisions`
  - 완료 팝업에 스킵/충돌 통계 표시

### 3.3 매크로 녹화 실동작 구현
- 상태: ✅ 완료
- 반영:
  - `run_action`, `execute_action` 매크로 액션 타입 추가
  - Action Console 성공 실행 명령을 녹화 세션에 기록
  - 매크로 페이지에 `녹화 시작`, `녹화 종료/저장` UI 추가

### 3.4 북마크 선택 삭제 구현
- 상태: ✅ 완료
- 반영:
  - 코어: `delete_selected_bookmarks`, `batch_delete_selected_bookmarks` 추가
  - Worker: `delete_selected` 모드, `selected_map(file -> names[])` 입력 지원
  - UI: 테이블 선택행 집계 후 선택 삭제 실행
  - 기본 저장 정책은 새 파일 저장(원본 보존)

### 3.5 Smart TOC 정확도 개선
- 상태: ✅ 완료
- 반영:
  - form-feed(`\f`) 기반 페이지 분할 적용(기존 `page=0` 고정 해소)
  - 가능 시 HWPX 스타일 힌트 보조 분석
  - 실패 시 패턴 기반 자동 폴백
  - `TocResult.analysis_mode` 추가

### 3.6 Action Console 저장 정책
- 상태: ✅ 완료
- 반영:
  - 저장 모드: `저장 안 함` / `새 파일 저장(기본)` / `원본 덮어쓰기`
  - 출력 경로 입력/선택 UI 추가
  - 기본 저장 경로 자동 생성: `<default_output_dir>/action_console/<원본명>_edited.hwp`
  - 결과 artifact 확장: `saved`, `saved_path`, `save_mode`

### 3.7 BookmarkWorker 성공 판정 정책
- 상태: ✅ 완료
- 반영:
  - 고정 `success=True` 제거
  - `success = (fail_count == 0)` 정책 적용
  - 부분 실패 요약 메시지(`error_message`) 제공

### 3.8 Doc Diff HTML 안전성
- 상태: ✅ 완료
- 반영:
  - 리포트 생성 시 파일명/타이틀/변경 텍스트 `html.escape` 처리

### 3.9 Hyperlink 임시 폴더 정리
- 상태: ✅ 완료
- 반영:
  - `TemporaryDirectory` 컨텍스트로 전환
  - `_on_finished`, `_on_error`, `closeEvent`에서 cleanup 보장

### 3.10 템플릿 ID 충돌 방지
- 상태: ✅ 완료
- 반영:
  - 사용자 템플릿 ID를 초 단위 timestamp에서 `uuid4` 기반으로 변경

### 3.11 문서 정합성
- 상태: ✅ 완료
- 반영:
  - `README.md` 기능 설명을 현재 구현 범위로 업데이트
  - 저장 정책(원본 보존 기본)과 신규 기능 반영
  - 최신 테스트 결과 반영

### 3.12 spec 정합성
- 상태: ✅ 완료
- 반영:
  - `hwp_master.spec` 배포 데이터에 최신 감사 문서 포함

## 4) 추가 테스트(신규/보강)
- `tests/test_data_inject_worker_csv.py`
- `tests/test_smart_toc_paging.py`
- `tests/test_doc_diff_html_escape.py`
- `tests/test_macro_recorder_action_console.py`
- `tests/test_bookmark_worker_policy.py`
- `tests/test_action_console_worker_save_policy.py`
- `tests/test_template_store_uuid.py`
- `tests/test_hwp_handler_security_mailmerge.py` (충돌 회피 시나리오 추가)
- `tests/test_qss_render.py` (토큰 기반 검증으로 정비)

## 5) 수용 조건 충족 여부
1. 감사 문서의 핵심 12개 항목 코드/문서 반영: ✅
2. 기본 저장 정책 원본 보존: ✅
3. 매크로 녹화/북마크 선택 삭제 UI 실동작: ✅
4. Smart TOC `page=0` 고정 해소(최소 form-feed 기반): ✅
5. 전체 회귀 통과: ✅ (`57 passed, 2 skipped`)

## 6) 남은 제약(명시)
- pyhwpx/한글 버전 차이로 HWPX 스타일 힌트 추출은 환경에 따라 제한될 수 있으며, 이 경우 패턴 기반 폴백으로 동작
- 실문서 통합 테스트는 환경 변수/런타임 의존으로 기본 skip

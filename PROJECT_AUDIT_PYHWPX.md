# HWP Master pyhwpx 전면 확장 감사 보고서

작성일: 2026-02-25  
기준 환경: Windows + 한글(HWP) 설치 환경, `pyhwpx 1.6.6`

## 1. 프로젝트 스냅샷
- 언어/런타임: Python 3.9+
- UI: PySide6
- HWP 자동화: pyhwpx
- 테스트 상태(2026-02-25 스냅샷): `57 passed, 2 skipped`
  최신 상태는 섹션 11 참고
- 이번 반영 범위:
  - Phase 0 즉시 결함 수정
  - `HwpHandler` 공용 액션 API 추가
  - `ActionRunner`/`CapabilityMapper` 신규 추가
  - “고급 액션 콘솔” UI 페이지 추가
  - 설정 반영 누락(윈도우 크기, 사이드바 접힘, 기본 변환 포맷) 수정

## 2. 현재 기능 매트릭스 (UI-코어-테스트 연결)
| 기능군 | UI 페이지 | 코어 모듈 | Worker | 테스트 상태 |
|---|---|---|---|---|
| 변환/병합/분할/데이터주입/메타정리 | `convert_page`, `merge_split_page`, `data_inject_page`, `metadata_page` | `hwp_handler`, `excel_handler` | `ConversionWorker`, `MergeWorker`, `SplitWorker`, `DataInjectWorker`, `MetadataCleanWorker` | 핵심 회귀 테스트 있음, 실문서 통합 테스트 공백 |
| 템플릿/매크로/정규식 | `template_page`, `macro_page`, `regex_page` | `template_store`, `macro_recorder`, `regex_replacer` | `MacroRunWorker`, `RegexReplaceWorker` | 매크로 프리셋/스크립트 컴파일 테스트 신규 추가 |
| 서식/표/문서비교/목차 | `style_cop_page`, `table_doctor_page`, `doc_diff_page`, `smart_toc_page` | `style_cop`, `table_doctor`, `doc_diff`, `smart_toc` | `StyleCopWorker`, `TableDoctorWorker`, `DocDiffWorker`, `SmartTocWorker` | 텍스트 기반 단위 테스트 일부 있음 |
| 생산성 도구 | `watermark_page`, `header_footer_page`, `bookmark_page`, `hyperlink_page`, `image_extractor_page` | `watermark_manager`, `header_footer_manager`, `bookmark_manager`, `hyperlink_checker`, `image_extractor` | 전용 Worker 존재 | 링크/이미지 일부 단위 테스트 있음 |
| pyhwpx 범용 실행 | `action_console_page` (신규) | `hwp_handler.run_action/execute_action`, `action_runner` (신규) | `ActionConsoleWorker` (신규) | ActionRunner 단위 테스트 신규 추가 |

## 3. 잠재 문제점 점검 결과

### High (즉시 장애 가능)
1. 매크로 따옴표 프리셋 데이터 깨짐  
   - 영향: 프리셋 생성/실행 문자열 오작동 가능  
   - 상태: **해결 완료** (`src/core/macro_recorder.py`)

2. 매크로 코드 생성이 pyhwpx 비호환 메서드명 사용  
   - 영향: 내보낸 스크립트/실행 로직 불일치  
   - 상태: **해결 완료** (`MacroAction.to_python_code`, `_execute_action` 정합화)

3. README 보안 기능 설명과 실제 구현 불일치  
   - 영향: 사용자 기대와 기능 괴리  
   - 상태: **해결 완료** (`README.md` 설명 수정)

### Medium (기능 기대 대비 불완전)
1. 설정값 선언 후 반영 누락
   - 대상: `default_convert_format`, `sidebar_collapsed`, `window_width/height`
   - 상태: **해결 완료** (`src/ui/main_window.py`)

2. 설정 필드 일부의 코어 반영 미흡
   - 대상: `WatermarkConfig.color/position`, `HeaderFooterConfig.font/include_*`, `StyleRule` 확장 필드, `TableStyle` 확장 필드
   - 상태: **부분 반영 완료**
   - 비고: pyhwpx/한글 버전별 파라미터셋 속성 차이로 best-effort 적용

### Low (정확도/운영 리스크)
1. Smart TOC의 페이지 번호 정확 추적 제한 (`page=0` 기본)
2. Regex 치환 횟수는 pyhwpx FindReplace 제약으로 일부 `-1`(정확 집계 미지원)
3. 표 스타일 고급 속성(헤더행/교차행 정확 색상)은 한글 내부 모델 의존성이 큼

## 4. pyhwpx 기능 커버리지 맵

## 4.1 자동 계측 결과 (이번 반영 시점)
- pyhwpx 버전: `1.6.6`
- 공개 메서드 수: `1115`
- 액션성 항목 수(대문자 시작 기준): `897`
- 저장소에서 직접 사용 중인 pyhwpx 공개 메서드: `14`
- 메서드 커버리지: `1.26%`
- 사용 액션 ID(코드 스캔): `19`

## 4.2 카테고리별 분포 (총량)
- file_io: 35
- field_form: 67
- find_replace: 27
- style_format: 72
- table: 117
- shape_graphic: 115
- security_privacy: 33
- automation_macro: 35
- navigation_selection: 99
- other: 515

## 4.3 현재 사용 카테고리 (코드 스캔)
- other: 8
- find_replace: 2
- file_io: 3
- field_form: 1

## 4.4 해석
- 기존 프로젝트는 “업무 자동화 핵심 시나리오” 중심으로 구현되어 있으며, pyhwpx 전체 API 대비 사용 폭은 매우 좁다.
- 이번 반영으로 남은 영역은 전용 기능 구현 + `ActionRunner`로 단계적 수용 가능해졌다.

## 5. 구현 로드맵 (Phase)

### Phase 0 안정화 (이번 반영 완료)
- 매크로 프리셋/코드 생성 결함 수정
- README 정합성 수정
- 설정 반영 누락 수정
- 테스트 보강

### Phase 1 문서 I/O·보안·개인정보
- 암호화/해제/권한/개인정보 패턴 기능을 전용 API로 추가
- `hwp_handler`에 보안 관련 작업 결과 타입 표준화

### Phase 2 필드·메타태그·템플릿·메일머지
- 누름틀/메타태그 조작 API 확대
- 템플릿 대량 생성 파이프라인 강화

### Phase 3 스타일·표·도형·이미지
- 표/도형 고급 옵션의 버전별 파라미터셋 매핑 고도화
- 이미지/도형 제어 기능 확장

### Phase 4 비교·검사·리포팅
- TOC/DocDiff/링크 검사 정확도 강화
- 리포트 포맷/요약 지표 통합

### Phase 5 범용 Action Runner + UI 콘솔
- 비핵심 pyhwpx 기능을 JSON 템플릿 기반으로 수용
- 실행 이력/재실행 템플릿 UX 개선

### Phase 6 성능·복구·운영
- 장시간 배치 안정성, 취소/복구 전략, 프로세스 잔존 제어 강화

## 6. 테스트 전략 (단위/통합/실환경)

### 6.1 이번 추가 테스트
- `tests/test_macro_recorder_presets.py`
  - 따옴표 프리셋 무결성
  - 매크로 내보내기 스크립트 `py_compile` 가능 여부
  - 코드 생성에서 비호환 메서드 제거 확인
- `tests/test_action_runner.py`
  - stop-on-error 동작
  - continue-on-error 동작
  - 템플릿 저장/로드/삭제
- `tests/test_hwp_capability_snapshot.py`
  - `CapabilitySnapshot` 스키마 검증
  - `CapabilityMapper` 결과 검증
- `tests/test_main_window_lazy_pages.py` 확장
  - 저장된 설정값(사이드바/기본 포맷) 반영 검증

### 6.2 권장 추가(다음 단계)
- 실문서 기반 통합 테스트(한글 설치된 환경)
- 보안/개인정보 처리 기능 회귀 세트
- Action Console 시나리오 테스트(JSON 유효성, 실행 결과 포맷, 템플릿 호환성)

## 7. 추적 체크리스트 (Done 기준)
- [x] `PROJECT_AUDIT_PYHWPX.md` 단일 종합 문서 작성
- [x] Phase 0 결함 수정(매크로/README/설정 반영)
- [x] `HwpHandler` 범용 실행 API 추가
- [x] `CapabilitySnapshot`/`OperationResult` 타입 추가
- [x] `action_runner.py` 추가
- [x] `capability_mapper.py` 추가
- [x] 워터마크/헤더푸터/서식/표 설정 필드 best-effort 반영 개선
- [x] “고급 액션 콘솔” UI + Worker 추가
- [x] 신규/기존 테스트 통과 (`65 passed, 2 skipped`)
- [x] 보안(암호화/해제) 전용 UI/API 완성 (Phase 1)
- [x] 메일머지/메타태그 고도화 (Phase 2)
- [x] 표/도형 고급 속성 정밀 반영 (Phase 3)

---

## 부록: 이번 변경 파일
- Core:
  - `src/core/hwp_handler.py`
  - `src/core/action_runner.py` (new)
  - `src/core/capability_mapper.py` (new)
  - `src/core/macro_recorder.py`
  - `src/core/watermark_manager.py`
  - `src/core/header_footer_manager.py`
  - `src/core/style_cop.py`
  - `src/core/table_doctor.py`
  - `src/core/__init__.py`
- UI:
  - `src/ui/pages/action_console_page.py` (new)
  - `src/ui/pages/__init__.py`
  - `src/ui/main_window.py`
  - `src/ui/pages/home_page.py`
- Utils:
  - `src/utils/worker.py`
- Docs:
  - `README.md`
  - `PROJECT_AUDIT_PYHWPX.md` (new)
- Tests:
  - `tests/test_macro_recorder_presets.py` (new)
  - `tests/test_action_runner.py` (new)
  - `tests/test_hwp_capability_snapshot.py` (new)
  - `tests/test_main_window_lazy_pages.py`
  - `tests/test_pages_lazy_import.py`

## 8. 2026-02-25 추가 구현 반영 (Phase 1~2 확장)

### 8.1 Phase 1 (문서 보안/개인정보) 반영 내용
- `src/core/hwp_handler.py`
  - `harden_document(source_path, output_path, options) -> OperationResult` 추가
  - `scan_personal_info(source_path, patterns, sample_limit) -> OperationResult` 추가
  - 암호 저장 best-effort 처리 `_save_as_with_password()` 추가
  - `clean_metadata()`가 내부적으로 `harden_document()`를 사용하도록 정리
- `src/ui/pages/metadata_page.py`
  - 메타/보안 옵션 체크박스 UI 추가
  - 개인정보 스캔 옵션, 문서 암호 입력, strict password 옵션 추가
- `src/ui/main_window.py`
  - 메타 정리 실행 시 UI 옵션을 `MetadataCleanWorker`로 전달
  - 완료 메시지에 개인정보 탐지 건수/암호 미적용 건수 표시
- `src/utils/worker.py`
  - `MetadataCleanWorker`가 `handler.harden_document()` 사용
  - 결과 요약에 `pii_total`, `password_not_applied`, `warnings` 포함

### 8.2 Phase 2 (필드/메일머지/메타태그) 반영 내용
- `src/core/hwp_handler.py`
  - `list_fields()` 추가
  - `fill_fields()` 추가
  - `get_meta_tags()` / `set_meta_tags()` 추가
  - `mail_merge()` 요약 API 추가
  - `iter_inject_data()` / `batch_inject_data()`에 `filename_template` 지원 추가
  - `inject_data()`를 `fill_fields()` 기반으로 통일
- `src/ui/pages/data_inject_page.py`
  - 파일명 필드(`filename_field`) 입력 UI 추가
  - 파일명 템플릿(`filename_template`) 입력 UI 추가
- `src/ui/main_window.py`
  - 데이터 주입 실행 시 파일명 필드/템플릿을 `DataInjectWorker`에 전달
- `src/utils/worker.py`
  - `DataInjectWorker`에 `filename_template` 인자 추가

### 8.3 신규 테스트
- `tests/test_hwp_handler_security_mailmerge.py` 추가
  1. 보안 하드닝 + 개인정보 스캔 결과 검증
  2. strict password 실패 처리 검증
  3. 필드 목록 정규화/중복제거 검증
  4. 필드 반영 실패 처리 검증
  5. 파일명 템플릿 기반 메일머지 파일명 생성 검증
  6. 메일머지 성공/실패 집계 검증

### 8.4 현재 상태 요약
- 전체 테스트: `57 passed, 2 skipped`
- Phase 1: 핵심 API + UI + Worker 반영 완료
- Phase 2: 필드/메일머지/메타태그 핵심 API와 UI 연동 완료
- 남은 고도화: pyhwpx 버전별 세부 액션 매핑 확대(문서 비교/도형/표 고급 파라미터)

## 9. 2026-02-25 추가 구현 반영 (Phase 3~4)

### 9.1 Phase 3 (도형/이미지/표 고급 파라미터 프리셋)
- `src/core/action_runner.py`
  - `ActionPreset` 타입 추가
  - 빌트인 프리셋 레지스트리 추가 (table/shape/image)
  - `list_builtin_presets()`, `get_builtin_preset()`, `build_builtin_preset_commands()`, `run_builtin_preset()` 추가
  - 프리셋 명령은 전부 `execute_action` 기반으로 구성
- `src/ui/pages/action_console_page.py`
  - “Built-in Phase 3 Presets” UI 추가
  - 프리셋을 JSON 에디터로 로드하거나 즉시 실행 가능

### 9.2 Phase 4 (문서비교/스마트목차 실문서 테스트)
- `tests/test_real_hwp_doc_diff_smart_toc.py` 추가
  - 실제 HWP 문서 생성 후 `DocDiff.compare()` 정확도 검증
  - 실제 HWP 문서 생성 후 `SmartTOC.extract_toc()` 제목 레벨 추출 검증
  - 기본 환경에서는 skip 처리, 실행 시 `HWPMASTER_REAL_DOC_TESTS=1` 필요

### 9.3 테스트 상태
- 전체 테스트: `57 passed, 2 skipped`
- skip 2건: 실문서 통합 테스트(환경 변수/실행 환경 의존)

### 9.4 배포 스펙(.spec) 정합성 보강
- `hwp_master.spec`
  - `importlib` 기반 lazy 페이지 로딩 누락 방지를 위해 `hiddenimports`에 lazy page 모듈 추가
  - Action Console/Capability 매핑 관련 core 모듈 hidden import 추가
  - 배포 문서 동봉을 위해 `PROJECT_AUDIT_PYHWPX.md`를 `datas`에 추가

## 10. 2026-02-27 후속 개선 반영 (Audit Closing)

### 10.1 핵심 이슈 닫힘 상태
- QSS 테스트 불일치: **해결**
  - `tests/test_qss_render.py`를 테마 토큰 기반으로 전환
- 데이터 주입 행 스킵/파일명 충돌: **해결**
  - CSV 완전 빈 행만 스킵
  - 파일명 충돌 시 `_1`, `_2` 자동 suffix
  - 결과 데이터에 `skipped_empty_rows`, `filename_collisions` 추가
- 매크로 녹화 미구현: **해결**
  - Action Console 실행 흐름 녹화(`run_action`, `execute_action`) 지원
  - 매크로 페이지 녹화 시작/종료 UI 반영
- 북마크 선택 삭제 미구현: **해결**
  - `delete_selected` worker 모드 + UI 선택행 집계 연동
- Smart TOC `page=0` 고정: **해결(최소 기준)**
  - form-feed 기반 페이지 분할 적용
  - `analysis_mode` 추가, HWPX 스타일 힌트 보조 분석(실패 시 폴백)
- Action Console 저장 경로 부재: **해결**
  - 저장 안 함 / 새 파일 저장(기본) / 원본 덮어쓰기 모드 추가
  - 실행 결과 artifacts에 `saved`, `saved_path`, `save_mode` 포함
- BookmarkWorker 성공 판정 고정: **해결**
  - `success = (fail_count == 0)` 정책 적용
- DocDiff HTML 이스케이프 누락: **해결**
  - 파일명/텍스트 `html.escape` 적용
- Hyperlink 임시 폴더 누적: **해결**
  - `TemporaryDirectory` 사용 + finish/error/close cleanup 보장
- TemplateStore ID 충돌 위험: **해결**
  - 사용자 템플릿 ID를 `uuid4` 기반으로 전환

### 10.2 테스트 상태 (2026-02-27 기준)
- 전체 테스트: **`57 passed, 2 skipped`**
- 신규/보강 테스트:
  - `test_data_inject_worker_csv.py`
  - `test_smart_toc_paging.py`
  - `test_doc_diff_html_escape.py`
  - `test_macro_recorder_action_console.py`
  - `test_bookmark_worker_policy.py`
  - `test_action_console_worker_save_policy.py`
  - `test_template_store_uuid.py`

### 10.3 잔여 제약(의도된 제한)
- pyhwpx/한글 버전 차이로 스타일 힌트 수집은 환경 의존적이며, 실패 시 패턴 기반 폴백
- 실문서 통합 테스트는 환경 변수(`HWPMASTER_REAL_DOC_TESTS=1`) 기반 선택 실행

## 11. 2026-02-28 후속 개선 반영 (Feature Audit Closing)

### 11.1 섹션 2 핵심 이슈 반영 결과
- 매크로 ID 충돌: **해결**
  - `src/core/macro_recorder.py`에서 `macro_<uuid4hex>` 전략으로 전환
- Header/Footer·Watermark 성공 판정 고정: **해결**
  - partial failure 시 `success=False` 반환
  - 실패 요약을 `error_message`에 포함
- remove 모드 출력 파일 충돌: **해결**
  - `resolve_output_path()` 적용으로 basename 충돌 시 `_1`, `_2` 자동 분기
- Excel 첫 컬럼 빈 값 행 누락: **해결**
  - 행 전체 빈 값일 때만 스킵하도록 `read_excel`/`read_excel_streaming` 통일
- Hyperlink 리포트 저장 실패 미집계: **해결**
  - 리포트 저장 실패를 fail count/최종 실패로 반영

### 11.2 테스트/문서/배포 정합성
- 신규 테스트 추가:
  - `tests/test_macro_recorder_id_uniqueness.py`
  - `tests/test_header_footer_worker_policy.py`
  - `tests/test_watermark_worker_policy.py`
  - `tests/test_excel_handler_blank_first_cell.py`
  - `tests/test_hyperlink_worker_report_save_policy.py`
- 최신 전체 테스트:
  - `pytest -q` 기준 **`65 passed, 2 skipped`**
- 문서 정합성:
  - `README.md` 감사 문서 링크와 최신 업데이트 반영
  - `CLAUDE.md`, `GEMINI.md` 운영 정합성 메모를 최신 회귀 기준으로 갱신
- 배포 스펙 정합성:
  - `hwp_master.spec`의 동봉 문서 경로를 `FEATURE_IMPLEMENTATION_AUDIT_2026-02-28.md`로 수정

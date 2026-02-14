# 추가 기술 점검 메모 (구현/운영 리스크 중심)

작성일: 2026-02-14  
참조: `CLAUDE.md`, `README.md`  
목적: “사용 중 사고(멈춤/취소불가/데이터손실) + 디버깅 불가(예외 삼키기) + 패키징/배포 누락”을 조기에 발견하고, 바로 이슈/PR 단위로 쪼갤 수 있게 근거 기반으로 정리합니다.

---

## 범위/원칙

- 이 문서는 “추가 점검” 문서입니다. 기능 설계 변경이 아니라 **현 구조에서 잠재적으로 깨질 수 있는 지점**을 우선순위(P0/P1/P2)로 정리합니다.
- 각 항목은 **근거(파일/패턴)** 와 함께 **영향, 권장 수정(결정 완료), 검증**을 포함합니다.

우선순위 정의:
- P0: 사용자 데이터 손실/앱 멈춤/크래시/보안 사고로 이어질 확률이 높음
- P1: 정확도/일관성/운영성 문제(로그/테스트/배포 등)
- P2: 완성도/정리/리팩터링(지금 안 해도 되지만 언젠가 비용이 커짐)

---

## 1) Repo/문서 정합성 이슈

- [P0] `PROJECT_AUDIT.md` 파일 정합성(협업/운영 혼선)
  **근거:** 점검 당시 repo 루트에 `PROJECT_AUDIT.md`가 누락되어(IDE 탭/가이드와 불일치) 협업/운영 혼선 여지가 있었습니다. 이후 `PROJECT_AUDIT.md`를 repo 루트에 추가해 엔트리를 복원했습니다.  
  **영향:** 점검 항목의 단일 소스가 사라져 운영/협업 혼선, “무엇을 고쳤고 무엇이 남았는지” 추적이 어려움.  
  **권장 수정:** `PROJECT_AUDIT.md`를 엔트리 문서로 유지하고, 상세 점검은 `PROJECT_AUDIT_EXTRA.md`에 누적합니다(README에 링크 유지).  
  **검증:** 새 문서 링크가 `README.md`에서 접근 가능하고, 새 클론 환경에서도 동일하게 확인 가능.

- [P1] 스타일시트 문서/구조 불일치 가능성(템플릿 우선 vs README 표기)
  **근거:** `assets/styles/style.qss`와 `assets/styles/style.template.qss`가 공존하고, 로더는 템플릿 우선(`src/utils/qss_renderer.py`). 반면 `README.md` 프로젝트 구조에는 `assets/styles/style.qss`만 단일 소스로 보이기 쉽습니다.  
  **영향:** “style.qss를 수정했는데 UI가 안 바뀜” 같은 혼란, 테마 시스템 이해 비용 증가.  
  **권장 수정:** `README.md`의 해당 섹션을 “템플릿 기반(style.template.qss) + fallback(style.qss)”로 명시하거나, style.qss를 완전 fallback로 분리(삭제는 금지, 빌드 fallback 필요). (진행: README 반영 완료)  
  **검증:** (수동) `style.template.qss` 토큰 수정 후 즉시 UI 반영. (수동) `style.template.qss`가 없을 때는 `style.qss`로 정상 fallback.

---

## 2) COM/스레드 안정성 리스크

- [P0] Core에서 `pyhwpx.Hwp(...)` 직접 생성 시 COM 초기화 의존성이 호출자에 숨을 수 있음
  **근거:** `src/core/hyperlink_checker.py`는 내부에서 `pyhwpx.Hwp(visible=False)`를 직접 생성합니다. Worker 경로(`src/utils/worker.py`)는 `com_context()`로 감싸지만, core가 단독 호출되는 경로에서는 COM 초기화가 누락될 수 있습니다.  
  **영향:** 사용 패턴이 바뀌거나(예: UI/Worker 밖에서 호출), 향후 재사용 시 “특정 PC에서만 크래시/행걸”로 재발할 수 있습니다.  
  **권장 수정(결정):** `HyperlinkChecker._ensure_hwp()` 내부에서 `com_context()`를 사용하거나, 최소한 런타임 방어(“COM 초기화는 호출자 책임”을 강제하고 안내 메시지 제공)를 추가합니다.  
  **검증:** (수동) Worker 없이 `HyperlinkChecker().extract_links()` 호출 시에도 크래시 없이 동작(또는 명확한 안내 에러). (코드) `pythoncom` 미설치 환경에서도 `com_context()`는 no-op로 안전.

- [P1] Manager류가 내부에 handler/COM 객체를 캐시(`self._handler`)하는 구조는 재진입/스레드 혼용에 취약
  **근거:** `src/core/watermark_manager.py`, `src/core/header_footer_manager.py`에서 `self._handler`를 멤버로 보관합니다.  
  **영향:** 동일 인스턴스를 재사용하거나(페이지 단위로 오래 살아있는 객체), 스레드가 섞이면 COM 객체 생명주기 꼬임 가능.  
  **권장 수정:** “Manager 인스턴스는 1 Worker run(1 스레드) 범위에서만 사용”을 명확히 문서화하고, 재진입 감지(동일 인스턴스 2회 동시 실행 방지) 또는 handler를 호출 범위 내 컨텍스트로 관리하도록 구조를 단순화합니다.  
  **검증:** 연속 실행/취소/에러 후 재실행에서도 `hwp.exe` 잔존이 최소화되고 동작이 안정적.

---

## 3) 예외 처리/로깅(디버깅 가능성)

- [P0] “실패했는데 조용히 False/0 반환” 패턴은 원인 파악을 막음
  **근거:**  
  `src/core/excel_handler.py`의 `write_excel()/write_csv()`는 `except Exception: return False` 패턴.  
  `src/core/image_extractor.py`의 `get_image_count()`는 예외 시 `0` 반환.  
  **영향:** 사용자 입장에서는 “성공한 줄 알았는데 결과가 없다”로 느껴지고, 개발자 입장에서는 재현/로그가 없어 원인 파악이 어려움.  
  **권장 수정(결정):** 최소 `logger.warning(..., exc_info=True)`로 실패 원인을 남기고, 가능하면 `Result` 타입(성공/실패 + error_message)을 반환하도록 개선합니다.  
  **검증:** 실패 시 `~/.hwp_master/logs`에 원인 로그가 남고, UI에도 “왜 실패했는지” 최소 메시지가 표시됨.

- [P1] 내부 cleanup 실패를 통째로 무시(디스크 누수/권한 문제 은닉)
  **근거:** `src/core/image_extractor.py`에서 임시 `*.hwpx` 삭제 실패를 `except Exception: pass`로 무시하는 구간.  
  **영향:** 읽기 전용 폴더/권한 이슈에서 임시 파일이 남아 디스크 누수 가능.  
  **권장 수정:** UX는 해치지 않되 debug/warning 로그를 1회 남겨 “왜 남았는지” 추적 가능하게 합니다.  
  **검증:** 읽기 전용 폴더에서 실행 시, 임시 파일 삭제 실패 로그가 남음.

---

## 4) 경로/파일명 안전성(Windows 특이 케이스)

- [P0] 파일명 sanitization이 “금지 문자 치환”까지만 커버(예약어/길이/말단 공백/점 미흡)
  **근거:** `src/core/hwp_handler.py` 데이터 주입 파일명은 금지문자만 치환하는 형태(예: `< > : \" / \\ | ? *` 정도)로 보이며, Windows 예약어(CON/PRN/AUX/NUL/COM1..), 말단 공백/점, 길이 제한 등의 처리가 없습니다.  
  **영향:** 특정 데이터(파일명 필드)에 따라 저장 실패, 대량 처리 중 일부만 실패 → 재시도 비용 증가.  
  **권장 수정(결정):** 공통 유틸 `sanitize_filename()`를 도입해 예약어/trim/길이 제한을 포함하고, data inject/template/리포트/엑셀 export 등 파일 생성 경로에 일괄 적용합니다.  
  **검증:** 예약어/긴 문자열/특수문자/말단 공백/점 입력 데이터로 생성 시도 → 충돌 없이 저장.

- [P0] 출력 폴더 기반 배치 작업에서 “파일명 충돌/덮어쓰기” 가능성이 남아있음
  **근거:**  
  `src/core/watermark_manager.py` `batch_apply_watermark()`는 `output_dir / Path(source).name`으로 저장.  
  `src/core/header_footer_manager.py` `batch_apply_header_footer()`도 동일.  
  `src/core/bookmark_manager.py` `batch_export_bookmarks()`는 `{stem}_bookmarks.xlsx`로 저장.  
  서로 다른 폴더의 `a.hwp`를 같은 output_dir에 넣으면 덮어쓰기가 발생할 수 있습니다.  
  **영향:** 결과 유실(조용한 overwrite), “몇 개는 사라졌다” 같은 사용 사고로 이어짐.  
  **권장 수정(결정):** `src/utils/output_paths.py`의 `resolve_output_path()`를 모든 “output_dir에 저장” 경로에 적용(워터마크/헤더푸터/북마크 엑셀/리포트 등).  
  **검증:** 동일 파일명이 섞인 입력(서로 다른 폴더의 `same.hwp`)을 처리해도 결과가 `_1`, `_2`로 안전하게 생성됨.

- [P1] “기본 출력 폴더” 정책은 확대됐지만 다이얼로그/기본 버튼 일관성 점검은 지속 필요
  **근거:** 각 페이지에서 `QFileDialog.*` 호출이 산재(`src/ui/main_window.py`, `src/ui/pages/*`). 기능 추가/변경 시 쉽게 일관성이 깨질 수 있음.  
  **영향:** 기능별 저장 위치 UX가 들쭉날쭉해 사용자가 헷갈림.  
  **권장 수정:** 다이얼로그 start dir은 `default_output_dir`로 통일하고, overwrite 확인의 기본 버튼은 `No`로 통일하는 규칙을 문서화(코드 리뷰 체크리스트 포함).  
  **검증:** 새 설치 후 어떤 기능을 먼저 눌러도 동일한 기본 폴더에서 시작.

---

## 5) 네트워크/보안/프라이버시

- [P0] 링크 검사 기능은 외부 URL에 실제로 접속(urllib)함
  **근거:** `src/core/hyperlink_checker.py`에서 `urllib.request.urlopen(..., timeout=...)` 호출.  
  **영향:** 민감 문서의 링크 검사 과정에서 외부 요청이 발생해 보안/프라이버시 이슈 가능(기업 환경에서 특히 중요).  
  **권장 수정(결정):**  
  “외부 접속 발생” 고지(최초 실행 또는 설정 화면), 외부 접속 비활성 옵션, 도메인 allowlist, timeout/UA 정책 설정을 추가합니다.  
  **검증:** 외부 접속 비활성 옵션 시 네트워크 요청이 0이며, 결과는 “검사 불가(정책)”로 명확히 표시됨.

- [P1] HTML 리포트 출력 시 HTML escaping 미흡 가능
  **근거:** 리포트가 문자열 조립 방식으로 생성되는 구간(링크 텍스트/URL/error_message). 입력이 문서에서 추출된 텍스트라면 `<script>` 같은 문자열이 포함될 수 있습니다.  
  **영향:** 로컬에서 열 때 예상치 못한 HTML 렌더링/스크립트 실행 가능성(낮지만 존재).  
  **권장 수정(결정):** 리포트 생성 시 `html.escape()`로 링크 텍스트/URL/error_message를 escape 합니다.  
  **검증:** `<script>alert(1)</script>`가 포함된 텍스트가 그대로 실행/렌더되지 않고 문자열로 표시됨.

---

## 6) 빌드/배포(Windows PyInstaller)

- [P0] `pywin32` 의존성 명시 여부 점검 필요
  **근거:** `hwp_master.spec`의 `hiddenimports`에 `win32com.client`, `pythoncom`가 포함되어 있습니다. `requirements.txt`에는 `pywin32`가 명시되지 않을 수 있습니다(환경에 따라 `pyhwpx`가 끌고 올 수도 있으나, 클린 환경 보장은 별개).  
  **영향:** 새 venv/클린 PC에서 설치/실행 실패.  
  **권장 수정(결정):** `requirements.txt`에 `pywin32`를 명시하거나, 설치 가이드에 명확히 적고 런타임에서 누락 시 안내를 제공합니다.  
  **검증:** 새 venv에서 `pip install -r requirements.txt` 후 실행 성공.

- [P1] `uac_admin=True`는 항상 관리자 권한 실행을 강제
  **근거:** `hwp_master.spec`에서 `uac_admin=True`.  
  **영향:** 기업 환경에서 배포/실행 장벽, 불필요한 권한 상승(보안 정책 위반 가능).  
  **권장 수정(결정):** 관리자 권한이 꼭 필요한 작업만 분리하거나, 기본은 비관리자로 실행하고 필요 시에만 안내/재실행 흐름을 제공합니다.  
  **검증:** 비관리자 실행에서도 핵심 기능이 동작하고, 권한이 필요한 기능은 명확한 안내가 뜸.

---

## 7) 테스트/검증 공백

- [P1] HWP/COM 의존 기능의 “순수 로직” 분리 테스트 확대 필요
  **근거:** COM/한글 설치가 필요한 기능은 CI에서 재현이 어렵고, 회귀가 UI에서 늦게 발견됩니다.  
  **영향:** 릴리즈 후에만 깨짐을 발견할 확률 상승.  
  **권장 수정(결정):** 아래 항목은 순수 함수/로직으로 분리해 unittest로 커버합니다.
  파일명 sanitize 로직, HTML escape, output 충돌 회피 로직, 링크 상태 판정(로컬 파일/timeout 처리), 엑셀 export 포맷(헤더/스타일) 등.  
  **검증:** 로직 변경 시 `python -m unittest -q`로 회귀가 즉시 탐지됨.

---

## 8) 코드/구조 품질 리스크 (CLAUDE.md 관점)

- [P2] 전역 싱글톤 패턴은 테스트/확장성을 떨어뜨릴 수 있음
  **근거:** `get_settings_manager()`, `get_history_manager()` 같은 전역 접근 패턴.  
  **영향:** 테스트 격리/멀티 인스턴스 실행/DI 적용이 어려워짐.  
  **권장 수정:** 당장 큰 변경이 아니면, 최소한 “읽기 전용”으로 쓰는 곳부터 주입(Dependency Injection) 패턴으로 단계적 전환을 권장합니다.  
  **검증:** Settings/History를 테스트에서 임시 디렉토리로 주입 가능.

- [P2] private 메서드/필드 접근은 회귀를 부른다
  **근거:** core/worker/recorder에서 `_ensure_hwp`, `_execute_action` 같은 내부 접근이 보일 수 있음(향후 refactor 시 깨질 수 있음).  
  **영향:** 작은 내부 변경이 전체 기능을 깨뜨림.  
  **권장 수정:** “public API만 호출” 규칙을 정하고, 필요한 기능은 public wrapper를 추가합니다.  
  **검증:** 내부 구현 변경 후에도 공개 API 계약이 유지되면 기능이 유지됨.

---

## 9) 운영/UX 추가 후보

- [P1] “한글(hwp.exe) 강제 종료” 기능은 위험도가 높아 안내/로그/권한 처리 강화 필요
  **근거:** 설정 화면에서 `taskkill`을 호출하는 기능이 존재할 수 있음(`taskkill /IM hwp.exe /T /F`).  
  **영향:** 저장되지 않은 문서 유실 위험.  
  **권장 수정:** 경고 문구 강화, 실행 전 “열려있는 문서 저장 여부 확인 불가”를 명시, 실행 로그 남기기.  
  **검증:** 사용자가 의도하지 않게 누르지 않도록 UI를 안전하게 구성(secondary/confirm).

---

## 완료 기준(이 문서 관점)

- 이 문서(`PROJECT_AUDIT_EXTRA.md`)가 repo 루트에 존재하고, 팀원이 파일만 열어도 무엇을 고칠지 즉시 이해 가능.
- 각 항목이 (근거/영향/권장 수정/검증) 4요소를 포함.
- P0/P1/P2로 우선순위가 매겨져 있고, PR 단위로 쪼개기 쉽다.

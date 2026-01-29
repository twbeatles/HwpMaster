# HWP Master

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![PySide6](https://img.shields.io/badge/PySide6-6.0+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

**pyhwpx 기반 경량 HWP 업무 자동화 올인원 도구**

## ✨ 특징

- **🪶 경량화**: Pandas/NumPy 없이 순수 Python으로 동작
- **🎨 모던 UI**: PySide6 기반 다크모드 대시보드
- **🔧 올인원**: 변환, 병합, 분할, 데이터 주입, 서식 교정 통합
- **📊 고급 분석**: 문서 비교, 자동 목차 생성

---

## 📋 요구사항

| 항목 | 요구 사양 |
|------|----------|
| OS | Windows 10/11 (64bit) |
| 한글 | 한글 2018 이상 설치 필수 |
| Python | 3.9 이상 |

---

## 🚀 설치 및 실행

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 프로그램 실행
python main.py
```

---

## 🎯 전체 기능 (v5.0)

### Phase 1 - 기본 기능 (v1.0)

| 기능 | 설명 | 사용법 |
|------|------|--------|
| **Smart Batch Converter** | HWP → PDF/TXT/HWPX/JPG 일괄 변환 | 사이드바 `🔄 변환` → 파일 드래그 → 포맷 선택 → 변환 실행 |
| **Merge & Split** | 파일 병합 및 페이지 분할 | 사이드바 `📎 병합/분할` → 파일 추가 → 모드 선택 |
| **Light Data Injector** | Excel 데이터를 HWP 누름틀에 주입 | 사이드바 `📝 데이터 주입` → HWP 템플릿 + Excel 선택 |
| **Metadata Cleaner** | 문서 메타정보 정리 | 사이드바 `🧹 메타정보 정리` → 파일 추가 → 실행 |

### Phase 2 - 고급 기능 (v2.0)

| 기능 | 설명 | 사용법 |
|------|------|--------|
| **템플릿 스토어** | 8종 내장 양식 (휴가계, 지출결의서 등) | 사이드바 `📦 템플릿` → 카드 클릭 → 데이터 입력 → 생성 |
| **매크로 레코더** | 반복 작업을 Python 스크립트로 저장 | 사이드바 `🎬 매크로` → 새 매크로 → 액션 추가 → 저장 |
| **정규식 치환기** | 11종 마스킹 프리셋 (주민번호, 전화번호 등) | 사이드바 `🔤 정규식` → 프리셋 선택 → 파일 추가 → 실행 |

### Phase 3 - 규정 준수 (v3.0)

| 기능 | 설명 | 사용법 |
|------|------|--------|
| **Style Cop** | 폰트/줄간격 강제 통일 | 사이드바 `👮 Style Cop` → 프리셋 선택 → 파일 추가 → 적용 |
| **Table Doctor** | 표 테두리/셀 여백 일괄 변경 | 사이드바 `🩺 Table Doctor` → 스타일 선택 → 적용 |

### Phase 4 - 고급 편집 (v4.0)

| 기능 | 설명 | 사용법 |
|------|------|--------|
| **Doc Diff** | 두 문서 비교 및 리포트 생성 | 사이드바 `📊 Doc Diff` → v1/v2 파일 선택 → 비교 실행 |
| **Smart TOC** | 자동 목차 추출 및 삽입 | 사이드바 `📑 Smart TOC` → 파일 선택 → 추출 → 삽입 |

### Phase 5 - 생산성 (v5.0)

| 기능 | 설명 | 사용법 |
|------|------|--------|
| **Watermark** | 텍스트/이미지 워터마크 일괄 삽입 | 사이드바 `💧 워터마크` → 프리셋/설정 → 적용 |
| **Header/Footer** | 헤더/푸터/페이지번호 일괄 설정 | 사이드바 `📄 헤더/푸터` → 프리셋/설정 → 적용 |
| **Bookmark** | 북마크 추출/삭제/Excel 내보내기 | 사이드바 `🔖 북마크` → 추출/삭제/내보내기 |
| **Hyperlink** | 문서 내 링크 유효성 검사 | 사이드바 `🔗 링크 검사` → 검사 시작 → 리포트 저장 |
| **Image Extractor** | 문서 내 이미지 일괄 추출 | 사이드바 `🖼️ 이미지 추출` → 저장 폴더 설정 → 추출 |

### UX 개선 (v5.0)

- **작업 히스토리**: 최근 수행한 100건의 작업 내역 자동 저장 및 조회
- **즐겨찾기 폴더**: 자주 사용하는 폴더 등록 관리
- **테마 커스터마이징**: 5가지 테마 프리셋 지원


---

## 📁 프로젝트 구조

```
hwp-master/
├── main.py                    # 프로그램 진입점
├── requirements.txt           # 의존성
├── assets/
│   └── styles/style.qss       # 다크모드 스타일시트
├── src/
│   ├── core/                  # 핵심 비즈니스 로직
│   │   ├── hwp_handler.py     # HWP 제어 (pyhwpx)
│   │   ├── excel_handler.py   # Excel 처리 (openpyxl)
│   │   ├── template_store.py  # 템플릿 관리
│   │   ├── macro_recorder.py  # 매크로 기록/재생
│   │   ├── regex_replacer.py  # 정규식 치환
│   │   ├── style_cop.py       # 서식 경찰
│   │   ├── table_doctor.py    # 표 주치의
│   │   ├── doc_diff.py        # 문서 비교
│   │   ├── smart_toc.py       # 목차 생성
│   │   ├── watermark_manager.py   # 워터마크 관리
│   │   ├── header_footer_manager.py # 헤더/푸터 관리
│   │   ├── bookmark_manager.py    # 북마크 관리
│   │   ├── hyperlink_checker.py   # 링크 검사
│   │   └── image_extractor.py     # 이미지 추출
│   ├── ui/                    # 사용자 인터페이스
│   │   ├── main_window.py     # 메인 윈도우 프레임
│   │   ├── pages/             # 페이지 컴포넌트
│   │   │   ├── home_page.py        # 홈 대시보드
│   │   │   ├── convert_page.py     # 변환 페이지
│   │   │   ├── merge_split_page.py # 병합/분할 페이지
│   │   │   ├── data_inject_page.py # 데이터 주입 페이지
│   │   │   ├── metadata_page.py    # 메타데이터 페이지
│   │   │   ├── settings_page.py    # 설정 페이지
│   │   │   ├── template_page.py    # 템플릿 페이지
│   │   │   ├── macro_page.py       # 매크로 페이지
│   │   │   ├── regex_page.py       # 정규식 페이지
│   │   │   ├── style_cop_page.py   # 서식 교정 페이지
│   │   │   ├── table_doctor_page.py # 표 교정 페이지
│   │   │   ├── doc_diff_page.py    # 문서 비교 페이지
│   │   │   ├── smart_toc_page.py   # 목차 페이지
│   │   │   ├── watermark_page.py   # 워터마크 페이지
│   │   │   ├── header_footer_page.py # 헤더/푸터 페이지
│   │   │   ├── bookmark_page.py    # 북마크 페이지
│   │   │   ├── hyperlink_page.py   # 링크 검사 페이지
│   │   │   └── image_extractor_page.py # 이미지 추출 페이지
│   │   └── widgets/           # 재사용 위젯
│   │       ├── file_list.py        # 파일 목록 위젯
│   │       ├── progress_card.py    # 진행률 카드
│   │       ├── feature_card.py     # 기능 선택 카드
│   │       ├── sidebar_button.py   # 사이드바 버튼
│   │       ├── toast.py            # 토스트 메시지
│   │       ├── page_header.py      # 페이지 헤더
│   │       ├── favorites_panel.py  # 즐겨찾기 패널
│   │       └── history_panel.py    # 작업 히스토리
│   └── utils/                 # 유틸리티
│       ├── worker.py          # QThread 백그라운드 작업
│       ├── logger.py          # 로깅 시스템
│       ├── settings.py        # 설정 관리 (JSON)
│       ├── theme_manager.py   # 테마 관리
│       └── history_manager.py # 히스토리 관리
└── tests/                     # 단위 테스트
```

---

## 🔧 프리셋 목록

### Style Cop 프리셋
| 프리셋 | 폰트 | 크기 | 줄간격 |
|--------|------|------|--------|
| 공문서 표준 | 맑은 고딕 | 11pt | 160% |
| 보고서 | 맑은 고딕 | 11pt | 180% |
| 논문 | 바탕 | 10pt | 200% |
| 제안서 | 맑은 고딕 | 11pt | 150% |

### 정규식 치환 프리셋
| 프리셋 | 패턴 | 예시 |
|--------|------|------|
| 주민번호 마스킹 | `\d{6}-\d{7}` | `901234-1234567` → `901234-*******` |
| 전화번호 마스킹 | `010-\d{4}-\d{4}` | `010-1234-5678` → `010-****-****` |
| 이메일 마스킹 | `[\w.]+@[\w.]+` | `test@test.com` → `t***@t***.com` |

---

## 📝 사용 예시

### 1. HWP → PDF 일괄 변환

1. 사이드바에서 `🔄 변환` 클릭
2. HWP 파일들을 파일 목록에 드래그앤드롭
3. 출력 포맷에서 `PDF` 선택
4. `변환 실행` 클릭
5. 결과 파일 저장 위치 선택

### 2. 주민번호 마스킹 처리

1. 사이드바에서 `🔤 정규식 치환` 클릭
2. `주민번호 마스킹` 프리셋 카드 클릭
3. 대상 HWP 파일 추가
4. `실행` 클릭

### 3. 문서 비교 리포트 생성

1. 사이드바에서 `📊 Doc Diff` 클릭
2. 원본 파일(v1) 선택
3. 수정 파일(v2) 선택
4. `비교 실행` 클릭
5. `리포트 저장`으로 HTML 리포트 내보내기

---

## ⚠️ 주의사항

- **한글 프로그램 필수**: pyhwpx는 한글 2018 이상이 설치된 환경에서만 동작합니다.
- **Windows 전용**: 한글 COM 인터페이스를 사용하므로 Windows에서만 실행 가능합니다.
- **백그라운드 실행**: 대량 파일 처리 시 한글이 백그라운드에서 실행됩니다.

---

## 📄 라이선스

MIT License

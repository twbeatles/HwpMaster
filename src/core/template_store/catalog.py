from __future__ import annotations

from .models import BuiltinTemplateSpec


BUILTIN_TEMPLATES: list[BuiltinTemplateSpec] = [
    {
        "id": "leave_annual",
        "name": "연차휴가 신청서",
        "description": "연차휴가 사용 신청을 위한 표준 양식",
        "category": "휴가",
        "fields": ["성명", "부서", "직급", "휴가기간", "휴가일수", "사유", "날짜"],
    },
    {
        "id": "leave_sick",
        "name": "병가 신청서",
        "description": "질병으로 인한 휴가 신청 양식",
        "category": "휴가",
        "fields": ["성명", "부서", "휴가기간", "병명", "첨부서류", "날짜"],
    },
    {
        "id": "expense_general",
        "name": "지출결의서",
        "description": "일반 경비 지출 결의 양식",
        "category": "지출",
        "fields": ["결재일", "부서", "품의자", "지출항목", "금액", "내역", "비고"],
    },
    {
        "id": "expense_travel",
        "name": "출장비 정산서",
        "description": "출장 경비 정산 양식",
        "category": "지출",
        "fields": ["성명", "부서", "출장기간", "출장지", "교통비", "숙박비", "식비", "합계"],
    },
    {
        "id": "meeting_minutes",
        "name": "회의록",
        "description": "회의 내용 기록 양식",
        "category": "회의",
        "fields": ["회의명", "일시", "장소", "참석자", "안건", "내용", "결정사항", "작성자"],
    },
    {
        "id": "report_weekly",
        "name": "주간업무보고",
        "description": "주간 업무 현황 보고 양식",
        "category": "보고서",
        "fields": ["보고기간", "부서", "성명", "금주실적", "차주계획", "특이사항"],
    },
    {
        "id": "report_project",
        "name": "프로젝트 완료보고서",
        "description": "프로젝트 완료 후 최종 보고 양식",
        "category": "보고서",
        "fields": ["프로젝트명", "기간", "담당자", "목표", "결과", "성과", "향후계획"],
    },
    {
        "id": "letter_official",
        "name": "대외공문",
        "description": "대외 발송용 공식 문서 양식",
        "category": "공문",
        "fields": ["문서번호", "수신", "참조", "제목", "본문", "발신일", "발신자"],
    },
]

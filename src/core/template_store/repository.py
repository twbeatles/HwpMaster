from __future__ import annotations

import json
from typing import Any

from ...utils.atomic_write import atomic_write_json
from .catalog import BUILTIN_TEMPLATES
from .models import TemplateInfo


def init_directories(store: Any) -> None:
    """디렉토리 초기화"""

    store._base_dir.mkdir(parents=True, exist_ok=True)
    store._templates_dir.mkdir(exist_ok=True)
    store._user_templates_dir.mkdir(exist_ok=True)


def load_metadata(store: Any) -> None:
    """메타데이터 로드"""

    if store._metadata_file.exists():
        try:
            with open(store._metadata_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("templates", []):
                    template = TemplateInfo.from_dict(item)
                    store._templates[template.id] = template
        except Exception as e:
            store._logger.warning(f"템플릿 메타데이터 로드 실패: {e}")


def save_metadata(store: Any) -> None:
    """메타데이터 저장"""

    data = {
        "version": "1.0",
        "templates": [template.to_dict() for template in store._templates.values()],
    }
    atomic_write_json(store._metadata_file, data, ensure_ascii=False, indent=2)


def init_builtin_templates(store: Any) -> None:
    """내장 템플릿 초기화"""

    changed = False
    for builtin in BUILTIN_TEMPLATES:
        template_id = builtin["id"]
        if template_id not in store._templates:
            store._templates[template_id] = TemplateInfo(
                id=template_id,
                name=builtin["name"],
                description=builtin["description"],
                category=builtin["category"],
                file_path="",
                is_builtin=True,
                fields=builtin.get("fields", []),
            )
            changed = True
    if changed:
        store._save_metadata()

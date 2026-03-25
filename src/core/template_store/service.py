from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from .models import TemplateInfo


def get_all_templates(store: Any) -> list[TemplateInfo]:
    return list(store._templates.values())


def get_templates_by_category(store: Any, category: str) -> list[TemplateInfo]:
    return [template for template in store._templates.values() if template.category == category]


def get_favorite_templates(store: Any) -> list[TemplateInfo]:
    return [template for template in store._templates.values() if template.is_favorite]


def get_recent_templates(store: Any, limit: int = 5) -> list[TemplateInfo]:
    sorted_templates = sorted(store._templates.values(), key=lambda template: template.used_count, reverse=True)
    return sorted_templates[:limit]


def get_template(store: Any, template_id: str) -> Optional[TemplateInfo]:
    return store._templates.get(template_id)


def add_user_template(
    store: Any,
    name: str,
    file_path: str,
    description: str = "",
    category: str = "기타",
) -> TemplateInfo:
    template_id = f"user_{uuid4().hex}"
    source = Path(file_path)
    dest = store._user_templates_dir / f"{template_id}{source.suffix}"
    shutil.copy2(source, dest)

    template = TemplateInfo(
        id=template_id,
        name=name,
        description=description,
        category=category,
        file_path=str(dest),
        is_builtin=False,
    )

    store._templates[template_id] = template
    store._save_metadata()
    return template


def remove_template(store: Any, template_id: str) -> bool:
    template = store._templates.get(template_id)
    if not template or template.is_builtin:
        return False

    if template.file_path:
        file_path = Path(template.file_path)
        if file_path.exists():
            file_path.unlink()

    del store._templates[template_id]
    store._save_metadata()
    return True


def toggle_favorite(store: Any, template_id: str) -> bool:
    template = store._templates.get(template_id)
    if template:
        template.is_favorite = not template.is_favorite
        store._save_metadata()
        return template.is_favorite
    return False


def increment_usage(store: Any, template_id: str) -> None:
    template = store._templates.get(template_id)
    if template:
        template.used_count += 1
        store._save_metadata()


def _resolve_output_path(template: TemplateInfo, output_path: str) -> Path:
    source = Path(template.file_path)
    source_suffix = source.suffix
    if not source_suffix:
        raise ValueError("원본 템플릿 확장자를 확인할 수 없습니다.")

    dest = Path(output_path)
    if not dest.suffix:
        dest = dest.with_suffix(source_suffix)

    if dest.suffix.lower() != source_suffix.lower():
        raise ValueError(
            f"출력 파일 확장자는 원본 템플릿과 같아야 합니다: {source_suffix}"
        )

    return dest


def use_template(store: Any, template_id: str, output_path: str) -> Optional[str]:
    template = store._templates.get(template_id)
    if not template:
        return None

    if not template.file_path:
        if template.is_builtin:
            raise ValueError(
                f"내장 템플릿 '{template.name}'의 HWP 파일이 없습니다. "
                f"'{template.name}' 템플릿 사용을 위해 먼저 HWP 파일을 등록해주세요."
            )
        return None

    source = Path(template.file_path)
    if not source.exists():
        store._logger.warning(f"템플릿 파일이 존재하지 않습니다: {template.file_path}")
        return None

    dest = _resolve_output_path(template, output_path)
    shutil.copy2(source, dest)
    store.increment_usage(template_id)
    return str(dest)


def create_from_template(
    store: Any,
    template_id: str,
    data: dict[str, str],
    output_path: str,
) -> Optional[str]:
    template = store._templates.get(template_id)
    if not template or not template.file_path:
        return None

    dest = _resolve_output_path(template, output_path)

    try:
        from src.core.hwp_handler import HwpHandler

        with HwpHandler() as handler:
            result = handler.inject_data(template.file_path, data, str(dest))

            if result.success:
                store.increment_usage(template_id)
                return result.output_path
    except Exception as e:
        store._logger.warning(f"템플릿 생성 중 오류 발생: {e}")

    return None


def search_templates(store: Any, query: str) -> list[TemplateInfo]:
    query_lower = query.lower()
    return [
        template
        for template in store._templates.values()
        if query_lower in template.name.lower()
        or query_lower in template.description.lower()
        or query_lower in template.category.lower()
    ]


def get_categories(store: Any) -> list[str]:
    categories = set(template.category for template in store._templates.values())
    return sorted(categories)


def register_builtin_template_file(store: Any, template_id: str, file_path: str) -> bool:
    template = store._templates.get(template_id)
    if not template or not template.is_builtin:
        store._logger.warning(f"내장 템플릿이 아니거나 존재하지 않는 ID: {template_id}")
        return False

    source = Path(file_path)
    if not source.exists():
        store._logger.warning(f"파일이 존재하지 않습니다: {file_path}")
        return False

    dest = store._templates_dir / f"{template_id}{source.suffix}"
    shutil.copy2(source, dest)

    template.file_path = str(dest)
    store._save_metadata()

    store._logger.info(f"내장 템플릿 '{template.name}'에 파일이 등록되었습니다: {dest}")
    return True


def get_unregistered_templates(store: Any) -> list[TemplateInfo]:
    return [template for template in store._templates.values() if template.is_builtin and not template.file_path]


def get_registered_templates(store: Any) -> list[TemplateInfo]:
    return [template for template in store._templates.values() if template.file_path and Path(template.file_path).exists()]


def is_template_ready(store: Any, template_id: str) -> bool:
    template = store._templates.get(template_id)
    if not template or not template.file_path:
        return False
    return Path(template.file_path).exists()

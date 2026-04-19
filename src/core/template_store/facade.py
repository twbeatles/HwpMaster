from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .catalog import BUILTIN_TEMPLATES
from .models import BuiltinTemplateSpec, TemplateCategory, TemplateInfo, TemplateStoreError
from .repository import init_builtin_templates, init_directories, load_metadata, save_metadata
from .service import (
    add_user_template,
    create_from_template,
    get_all_templates,
    get_categories,
    get_favorite_templates,
    get_recent_templates,
    get_registered_templates,
    get_template,
    get_templates_by_category,
    get_unregistered_templates,
    increment_usage,
    is_template_ready,
    register_builtin_template_file,
    remove_template,
    search_templates,
    toggle_favorite,
    use_template,
)


class TemplateStore:
    """
    템플릿 스토어 관리 클래스
    내장 템플릿 및 사용자 템플릿 관리
    """

    BUILTIN_TEMPLATES: list[BuiltinTemplateSpec] = BUILTIN_TEMPLATES
    Error = TemplateStoreError

    def __init__(self, base_dir: Optional[str] = None) -> None:
        self._logger = logging.getLogger(__name__)

        if base_dir:
            self._base_dir = Path(base_dir)
        else:
            self._base_dir = Path.home() / ".hwp_master" / "templates"

        self._templates_dir = self._base_dir / "files"
        self._user_templates_dir = self._base_dir / "user"
        self._metadata_file = self._base_dir / "templates.json"

        self._templates: dict[str, TemplateInfo] = {}

        self._init_directories()
        self._load_metadata()
        self._init_builtin_templates()

    def _init_directories(self) -> None:
        init_directories(self)

    def _load_metadata(self) -> None:
        load_metadata(self)

    def _save_metadata(self) -> None:
        save_metadata(self)

    def _init_builtin_templates(self) -> None:
        init_builtin_templates(self)

    def get_all_templates(self) -> list[TemplateInfo]:
        return get_all_templates(self)

    def get_templates_by_category(self, category: str) -> list[TemplateInfo]:
        return get_templates_by_category(self, category)

    def get_favorite_templates(self) -> list[TemplateInfo]:
        return get_favorite_templates(self)

    def get_recent_templates(self, limit: int = 5) -> list[TemplateInfo]:
        return get_recent_templates(self, limit)

    def get_template(self, template_id: str) -> Optional[TemplateInfo]:
        return get_template(self, template_id)

    def add_user_template(
        self,
        name: str,
        file_path: str,
        description: str = "",
        category: str = "기타",
    ) -> TemplateInfo:
        return add_user_template(self, name, file_path, description=description, category=category)

    def remove_template(self, template_id: str) -> bool:
        return remove_template(self, template_id)

    def toggle_favorite(self, template_id: str) -> bool:
        return toggle_favorite(self, template_id)

    def increment_usage(self, template_id: str) -> None:
        increment_usage(self, template_id)

    def use_template(self, template_id: str, output_path: str) -> Optional[str]:
        return use_template(self, template_id, output_path)

    def create_from_template(
        self,
        template_id: str,
        data: dict[str, str],
        output_path: str,
    ) -> Optional[str]:
        return create_from_template(self, template_id, data, output_path)

    def search_templates(self, query: str) -> list[TemplateInfo]:
        return search_templates(self, query)

    def get_categories(self) -> list[str]:
        return get_categories(self)

    def register_builtin_template_file(self, template_id: str, file_path: str) -> bool:
        return register_builtin_template_file(self, template_id, file_path)

    def get_unregistered_templates(self) -> list[TemplateInfo]:
        return get_unregistered_templates(self)

    def get_registered_templates(self) -> list[TemplateInfo]:
        return get_registered_templates(self)

    def is_template_ready(self, template_id: str) -> bool:
        return is_template_ready(self, template_id)

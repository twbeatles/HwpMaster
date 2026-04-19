from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from ...utils.history_manager import TaskType
from ...utils.qss_renderer import build_stylesheet
from ...utils.task_tracking import record_task_result, track_recent_files
from ...utils.worker import (
    ConversionWorker,
    DataInjectWorker,
    MergeWorker,
    MetadataCleanWorker,
    SplitWorker,
    WorkerResult,
)


def _bind_recent_file_tracking(window: Any, page: Any) -> None:
    file_list = getattr(page, "file_list", None)
    if file_list is None or not hasattr(file_list, "files_changed"):
        return
    file_list.files_changed.connect(lambda files, _window=window: track_recent_files(files, settings=_window._settings))


def sync_settings_page(window: Any) -> None:
    default_output_dir = window._settings.get("default_output_dir", "")
    if default_output_dir:
        window.settings_page.output_label.setText(default_output_dir)
        window.convert_page.output_label.setText(default_output_dir)
        window.metadata_page.output_label.setText(default_output_dir)
        window.data_inject_page.output_label.setText(default_output_dir)

    default_convert_format = str(window._settings.get("default_convert_format", "PDF")).upper()
    matched = False
    for btn in window.convert_page.format_buttons:
        is_match = btn.text().upper() == default_convert_format
        btn.setChecked(is_match)
        matched = matched or is_match
    if not matched and window.convert_page.format_buttons:
        window.convert_page.format_buttons[0].setChecked(True)

    preset = window._settings.get("theme_preset", "Dark (기본)")
    if hasattr(window.settings_page, "theme_combo"):
        idx = window.settings_page.theme_combo.findText(preset)
        if idx >= 0:
            window.settings_page.theme_combo.setCurrentIndex(idx)

    if hasattr(window.settings_page, "hyperlink_external_checkbox"):
        cb = window.settings_page.hyperlink_external_checkbox
        cb.blockSignals(True)
        cb.setChecked(bool(window._settings.get("hyperlink_external_requests_enabled", True)))
        cb.blockSignals(False)

    if hasattr(window.settings_page, "hyperlink_timeout_spin"):
        sp = window.settings_page.hyperlink_timeout_spin
        sp.blockSignals(True)
        try:
            sp.setValue(int(window._settings.get("hyperlink_timeout_sec", 5)))
        except Exception:
            sp.setValue(5)
        sp.blockSignals(False)

    if hasattr(window.settings_page, "hyperlink_allowlist_edit"):
        ed = window.settings_page.hyperlink_allowlist_edit
        ed.blockSignals(True)
        ed.setText(str(window._settings.get("hyperlink_domain_allowlist", "")))
        ed.blockSignals(False)


def apply_theme_preset(window: Any, preset: str) -> None:
    try:
        app = QApplication.instance()
        if not isinstance(app, QApplication):
            return
        app.setStyleSheet(build_stylesheet(preset))
    except Exception as e:
        from ...utils.logger import get_logger

        get_logger(__name__).warning(f"테마 적용 실패: {e}")


def cancel_current_worker(window: Any) -> None:
    if window._current_worker is not None:
        try:
            window._current_worker.cancel()
        except Exception as e:
            from ...utils.logger import get_logger

            get_logger(__name__).warning(f"worker.cancel() 호출 실패(무시): {e}")


def connect_signals(window: Any) -> None:
    _bind_recent_file_tracking(window, window.convert_page)
    _bind_recent_file_tracking(window, window.merge_split_page)
    _bind_recent_file_tracking(window, window.metadata_page)

    window.convert_page.convert_btn.clicked.connect(window._on_convert)
    window.convert_page.output_btn.clicked.connect(window._select_output_dir)
    window.convert_page.progress_card.cancelled.connect(window._cancel_current_worker)

    window.merge_split_page.execute_btn.clicked.connect(window._on_merge_split)
    window.merge_split_page.progress_card.cancelled.connect(window._cancel_current_worker)

    window.data_inject_page.template_btn.clicked.connect(window._select_template)
    window.data_inject_page.data_btn.clicked.connect(window._select_data_file)
    window.data_inject_page.execute_btn.clicked.connect(window._on_inject)
    window.data_inject_page.output_btn.clicked.connect(window._select_output_dir)
    window.data_inject_page.progress_card.cancelled.connect(window._cancel_current_worker)

    window.metadata_page.execute_btn.clicked.connect(window._on_clean_metadata)
    window.metadata_page.output_btn.clicked.connect(window._select_output_dir)
    window.metadata_page.progress_card.cancelled.connect(window._cancel_current_worker)

    window.settings_page.output_btn.clicked.connect(window._select_output_dir)
    if hasattr(window.settings_page, "theme_preset_changed"):
        window.settings_page.theme_preset_changed.connect(window._on_theme_preset_changed)
    if hasattr(window.settings_page, "hyperlink_external_requests_enabled_changed"):
        window.settings_page.hyperlink_external_requests_enabled_changed.connect(
            lambda v: window._settings.set("hyperlink_external_requests_enabled", bool(v))
        )
    if hasattr(window.settings_page, "hyperlink_timeout_sec_changed"):
        window.settings_page.hyperlink_timeout_sec_changed.connect(window._on_hyperlink_timeout_sec_changed)
    if hasattr(window.settings_page, "hyperlink_domain_allowlist_changed"):
        window.settings_page.hyperlink_domain_allowlist_changed.connect(window._on_hyperlink_allowlist_changed)


def on_theme_preset_changed(window: Any, preset: str) -> None:
    window._settings.set("theme_preset", preset)
    apply_theme_preset(window, preset)


def on_hyperlink_timeout_sec_changed(window: Any, value: int) -> None:
    window._settings.set("hyperlink_timeout_sec", int(value), defer=True)


def on_hyperlink_allowlist_changed(window: Any, value: str) -> None:
    window._settings.set("hyperlink_domain_allowlist", str(value), defer=True)


def on_page_changed(window: Any, index: int) -> None:
    if not (0 <= index < window._TOTAL_PAGE_COUNT):
        return
    window._ensure_page_loaded(index)
    window.page_stack.setCurrentIndex(index)
    if index == 0:
        window.home_page.refresh_panels()


def on_convert(window: Any) -> None:
    files = window.convert_page.file_list.get_files()
    if not files:
        QMessageBox.warning(window, "알림", "변환할 파일을 추가해주세요.")
        return

    target_format = "PDF"
    for btn in window.convert_page.format_buttons:
        if btn.isChecked():
            target_format = btn.text()
            break
    window._settings.set("default_convert_format", target_format, defer=True)

    window.convert_page.progress_card.setVisible(True)
    window.convert_page.progress_card.set_status("변환 준비 중...")
    window.convert_page.convert_btn.setEnabled(False)
    window.convert_page.progress_card.reset()

    window.set_busy(True)
    out_dir = str(Path(window._get_default_output_dir()) / "converted" / target_format.lower())
    window._current_worker = ConversionWorker(files, target_format, output_dir=out_dir)
    window._current_worker.progress.connect(
        lambda c, t, n: (
            window.convert_page.progress_card.set_count(c, t),
            window.convert_page.progress_card.set_current_file(n),
        )
    )
    window._current_worker.status_changed.connect(lambda s: window.convert_page.progress_card.set_status(s))
    window._current_worker.finished_with_result.connect(window._on_convert_finished)
    window._current_worker.start()


def on_convert_finished(window: Any, result: WorkerResult) -> None:
    window.set_busy(False)
    window.convert_page.convert_btn.setEnabled(True)
    files = window.convert_page.file_list.get_files()
    target_format = "PDF"
    for btn in window.convert_page.format_buttons:
        if btn.isChecked():
            target_format = btn.text()
            break
    if result.data and result.data.get("cancelled"):
        window.convert_page.progress_card.set_error("작업이 취소되었습니다.")
        QMessageBox.information(window, "취소", "변환 작업이 취소되었습니다.")
        return

    record_task_result(
        TaskType.CONVERT,
        f"{target_format} 변환",
        files,
        result,
        options={"target_format": target_format},
        settings=window._settings,
        history_manager=window._history,
    )

    if result.success:
        data = result.data or {}
        success_count = data.get("success_count", 0)
        fail_count = data.get("fail_count", 0)
        window.convert_page.progress_card.set_completed(success_count, fail_count)
        QMessageBox.information(
            window,
            "완료",
            f"변환이 완료되었습니다.\n성공: {success_count}개, 실패: {fail_count}개",
        )
    else:
        window.convert_page.progress_card.set_error(result.error_message or "오류 발생")
        QMessageBox.warning(window, "오류", result.error_message or "변환 중 오류가 발생했습니다.")


def on_merge_split(window: Any) -> None:
    files = window.merge_split_page.file_list.get_files()
    if not files:
        QMessageBox.warning(window, "알림", "파일을 추가해주세요.")
        return

    is_merge = window.merge_split_page.merge_btn.isChecked()

    window.merge_split_page.progress_card.setVisible(True)
    window.merge_split_page.progress_card.set_status("처리 준비 중...")
    window.merge_split_page.execute_btn.setEnabled(False)

    if is_merge:
        output_path, _ = QFileDialog.getSaveFileName(
            window,
            "병합 파일 저장",
            str(Path(window._get_default_output_dir()) / "merged.hwp"),
            "HWP 파일 (*.hwp)",
        )
        if not output_path:
            window.merge_split_page.execute_btn.setEnabled(True)
            window.merge_split_page.progress_card.setVisible(False)
            return

        window._pending_merge_output_path = output_path
        window.set_busy(True)
        window._current_worker = MergeWorker(files, output_path)
        window._current_worker.progress.connect(lambda c, t, n: window.merge_split_page.progress_card.set_count(c, t))
        window._current_worker.finished_with_result.connect(window._on_merge_finished)
        window._current_worker.start()
    else:
        if len(files) > 1:
            QMessageBox.warning(window, "알림", "분할은 한 번에 하나의 파일만 처리할 수 있습니다.")
            window.merge_split_page.execute_btn.setEnabled(True)
            window.merge_split_page.progress_card.setVisible(False)
            return

        page_ranges = window.merge_split_page.get_page_ranges()
        if not page_ranges:
            QMessageBox.warning(window, "알림", "페이지 범위를 입력해주세요.\n예: 1-3, 4-6")
            window.merge_split_page.execute_btn.setEnabled(True)
            window.merge_split_page.progress_card.setVisible(False)
            return

        output_dir = QFileDialog.getExistingDirectory(window, "분할 파일 저장 위치", window._get_default_output_dir())
        if not output_dir:
            window.merge_split_page.execute_btn.setEnabled(True)
            window.merge_split_page.progress_card.setVisible(False)
            return

        window.set_busy(True)
        window._current_worker = SplitWorker(files[0], page_ranges, output_dir)
        window._current_worker.progress.connect(lambda c, t, n: window.merge_split_page.progress_card.set_count(c, t))
        window._current_worker.status_changed.connect(lambda s: window.merge_split_page.progress_card.set_status(s))
        window._current_worker.finished_with_result.connect(window._on_split_finished)
        window._current_worker.start()


def on_merge_finished(window: Any, result: WorkerResult) -> None:
    window.set_busy(False)
    window.merge_split_page.execute_btn.setEnabled(True)
    files = window.merge_split_page.file_list.get_files()
    if result.data and result.data.get("cancelled"):
        window.merge_split_page.progress_card.set_error("작업이 취소되었습니다.")
        QMessageBox.information(window, "취소", "병합 작업이 취소되었습니다.")
        return

    record_task_result(
        TaskType.MERGE,
        "문서 병합",
        files,
        result,
        options={"output_path": getattr(window, "_pending_merge_output_path", "")},
        settings=window._settings,
        history_manager=window._history,
        recent_files=[getattr(window, "_pending_merge_output_path", "")],
    )

    if result.success:
        window.merge_split_page.progress_card.set_completed(1, 0)
        QMessageBox.information(window, "완료", "파일 병합이 완료되었습니다.")
    else:
        window.merge_split_page.progress_card.set_error(result.error_message or "오류 발생")
        QMessageBox.warning(window, "오류", result.error_message or "병합 중 오류가 발생했습니다.")


def on_split_finished(window: Any, result: WorkerResult) -> None:
    window.set_busy(False)
    window.merge_split_page.execute_btn.setEnabled(True)
    files = window.merge_split_page.file_list.get_files()
    if result.data and result.data.get("cancelled"):
        window.merge_split_page.progress_card.set_error("작업이 취소되었습니다.")
        QMessageBox.information(window, "취소", "분할 작업이 취소되었습니다.")
        return

    record_task_result(
        TaskType.SPLIT,
        "문서 분할",
        files,
        result,
        options={"page_ranges": window.merge_split_page.get_page_ranges()},
        settings=window._settings,
        history_manager=window._history,
    )

    if result.success:
        data = result.data or {}
        success_count = data.get("success_count", 0)
        fail_count = data.get("fail_count", 0)
        window.merge_split_page.progress_card.set_completed(success_count, fail_count)
        QMessageBox.information(
            window,
            "완료",
            f"파일 분할이 완료되었습니다.\n성공: {success_count}개, 실패: {fail_count}개",
        )
    else:
        window.merge_split_page.progress_card.set_error(result.error_message or "오류 발생")
        QMessageBox.warning(window, "오류", result.error_message or "분할 중 오류가 발생했습니다.")


def select_template(window: Any) -> None:
    file_path, _ = QFileDialog.getOpenFileName(
        window,
        "템플릿 파일 선택",
        window._get_default_output_dir(),
        "HWP 파일 (*.hwp *.hwpx)",
    )
    if file_path:
        window.data_inject_page.template_label.setText(file_path)
        window.data_inject_page.template_label.setStyleSheet("color: #e8e8e8;")
        track_recent_files([file_path], settings=window._settings)


def select_data_file(window: Any) -> None:
    file_path, _ = QFileDialog.getOpenFileName(
        window,
        "데이터 파일 선택",
        window._get_default_output_dir(),
        "Excel 파일 (*.xlsx *.xls);;CSV 파일 (*.csv)",
    )
    if file_path:
        window.data_inject_page.data_label.setText(file_path)
        window.data_inject_page.data_label.setStyleSheet("color: #e8e8e8;")
        track_recent_files([file_path], settings=window._settings)


def on_inject(window: Any) -> None:
    template = window.data_inject_page.template_label.text()
    data_file = window.data_inject_page.data_label.text()

    if "선택된 파일 없음" in template:
        QMessageBox.warning(window, "알림", "템플릿 파일을 선택해주세요.")
        return

    if "선택된 파일 없음" in data_file:
        QMessageBox.warning(window, "알림", "데이터 파일을 선택해주세요.")
        return

    output_dir = str(Path(window._get_default_output_dir()) / "data_injected")
    try:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        QMessageBox.warning(window, "오류", f"출력 폴더 생성 실패:\n{output_dir}\n\n{e}")
        return

    window.data_inject_page.progress_card.setVisible(True)
    window.data_inject_page.progress_card.reset()
    window.data_inject_page.progress_card.set_status("문서 생성 중...")
    window.data_inject_page.execute_btn.setEnabled(False)

    window.set_busy(True)
    filename_field = ""
    filename_template = ""
    if hasattr(window.data_inject_page, "filename_field_edit"):
        filename_field = window.data_inject_page.filename_field_edit.text().strip()
    if hasattr(window.data_inject_page, "filename_template_edit"):
        filename_template = window.data_inject_page.filename_template_edit.text().strip()

    window._current_worker = DataInjectWorker(
        template,
        data_file,
        output_dir,
        filename_field=filename_field or None,
        filename_template=filename_template or None,
    )
    window._current_worker.progress.connect(
        lambda c, t, n: (
            window.data_inject_page.progress_card.set_count(c, t),
            window.data_inject_page.progress_card.set_current_file(n),
        )
    )
    window._current_worker.status_changed.connect(lambda s: window.data_inject_page.progress_card.set_status(s))
    window._current_worker.finished_with_result.connect(window._on_inject_finished)
    window._current_worker.start()


def on_inject_finished(window: Any, result: WorkerResult) -> None:
    window.set_busy(False)
    window.data_inject_page.execute_btn.setEnabled(True)
    template = window.data_inject_page.template_label.text()
    data_file = window.data_inject_page.data_label.text()
    tracked_files = [path for path in [template, data_file] if "선택된 파일 없음" not in str(path)]
    if result.data and result.data.get("cancelled"):
        window.data_inject_page.progress_card.set_error("작업이 취소되었습니다.")
        QMessageBox.information(window, "취소", "데이터 주입 작업이 취소되었습니다.")
        return

    filename_field_edit = getattr(window.data_inject_page, "filename_field_edit", None)
    filename_template_edit = getattr(window.data_inject_page, "filename_template_edit", None)
    filename_field = filename_field_edit.text().strip() if filename_field_edit is not None else ""
    filename_template = (
        filename_template_edit.text().strip() if filename_template_edit is not None else ""
    )

    record_task_result(
        TaskType.DATA_INJECT,
        "데이터 주입",
        tracked_files,
        result,
        options={
            "filename_field": filename_field,
            "filename_template": filename_template,
        },
        settings=window._settings,
        history_manager=window._history,
    )

    if result.success:
        data = result.data or {}
        success_count = data.get("success_count", 0)
        fail_count = data.get("fail_count", 0)
        skipped_empty_rows = int(data.get("skipped_empty_rows", 0) or 0)
        filename_collisions = int(data.get("filename_collisions", 0) or 0)
        window.data_inject_page.progress_card.set_completed(success_count, fail_count)
        lines = [
            "데이터 주입이 완료되었습니다.",
            f"성공: {success_count}개, 실패: {fail_count}개",
        ]
        if skipped_empty_rows > 0:
            lines.append(f"완전 빈 행 스킵: {skipped_empty_rows}개")
        if filename_collisions > 0:
            lines.append(f"파일명 충돌 자동 회피: {filename_collisions}건")
        QMessageBox.information(window, "완료", "\n".join(lines))
    else:
        window.data_inject_page.progress_card.set_error(result.error_message or "오류 발생")
        QMessageBox.warning(window, "오류", result.error_message or "데이터 주입 중 오류가 발생했습니다.")


def on_clean_metadata(window: Any) -> None:
    files = window.metadata_page.file_list.get_files()
    if not files:
        QMessageBox.warning(window, "알림", "파일을 추가해주세요.")
        return

    window.metadata_page.progress_card.setVisible(True)
    window.metadata_page.progress_card.set_status("메타정보 정리 중...")
    window.metadata_page.execute_btn.setEnabled(False)

    window.set_busy(True)
    out_dir = str(Path(window._get_default_output_dir()) / "metadata_cleaned")
    options = {
        "remove_author": window.metadata_page.remove_author_check.isChecked(),
        "remove_comments": window.metadata_page.remove_comments_check.isChecked(),
        "remove_tracking": window.metadata_page.remove_tracking_check.isChecked(),
        "set_distribution": window.metadata_page.set_distribution_check.isChecked(),
        "scan_personal_info": window.metadata_page.scan_pii_check.isChecked(),
        "document_password": window.metadata_page.password_edit.text().strip(),
        "strict_password": window.metadata_page.strict_password_check.isChecked(),
    }

    window._current_worker = MetadataCleanWorker(files, output_dir=out_dir, options=options)
    window._current_worker.progress.connect(lambda c, t, n: window.metadata_page.progress_card.set_count(c, t))
    window._current_worker.status_changed.connect(lambda s: window.metadata_page.progress_card.set_status(s))
    window._current_worker.finished_with_result.connect(window._on_metadata_finished)
    window._current_worker.start()


def on_metadata_finished(window: Any, result: WorkerResult) -> None:
    window.set_busy(False)
    window.metadata_page.execute_btn.setEnabled(True)
    files = window.metadata_page.file_list.get_files()
    if result.data and result.data.get("cancelled"):
        window.metadata_page.progress_card.set_error("작업이 취소되었습니다.")
        QMessageBox.information(window, "취소", "메타정보 정리 작업이 취소되었습니다.")
        return

    record_task_result(
        TaskType.METADATA,
        "메타정보 정리",
        files,
        result,
        options={
            "remove_author": window.metadata_page.remove_author_check.isChecked(),
            "remove_comments": window.metadata_page.remove_comments_check.isChecked(),
            "remove_tracking": window.metadata_page.remove_tracking_check.isChecked(),
            "set_distribution": window.metadata_page.set_distribution_check.isChecked(),
            "scan_personal_info": window.metadata_page.scan_pii_check.isChecked(),
            "strict_password": window.metadata_page.strict_password_check.isChecked(),
        },
        settings=window._settings,
        history_manager=window._history,
    )

    if result.success:
        data = result.data or {}
        success_count = data.get("success_count", 0)
        fail_count = data.get("fail_count", 0)
        pii_total = int(data.get("pii_total", 0) or 0)
        password_not_applied = int(data.get("password_not_applied", 0) or 0)
        window.metadata_page.progress_card.set_completed(success_count, fail_count)
        detail_lines = [
            "메타정보 정리가 완료되었습니다.",
            f"성공: {success_count}개, 실패: {fail_count}개",
        ]
        if pii_total > 0:
            detail_lines.append(f"개인정보 패턴 탐지: {pii_total}건")
        if password_not_applied > 0:
            detail_lines.append(f"암호 미적용 파일: {password_not_applied}개")
        QMessageBox.information(window, "완료", "\n".join(detail_lines))
    else:
        window.metadata_page.progress_card.set_error(result.error_message or "오류 발생")
        QMessageBox.warning(window, "오류", result.error_message or "메타정보 정리 중 오류가 발생했습니다.")


def select_output_dir(window: Any) -> None:
    dir_path = QFileDialog.getExistingDirectory(window, "출력 폴더 선택", window._get_default_output_dir())
    if dir_path:
        window._settings.set("default_output_dir", dir_path)
        window.settings_page.output_label.setText(dir_path)
        window.convert_page.output_label.setText(dir_path)
        window.metadata_page.output_label.setText(dir_path)
        window.data_inject_page.output_label.setText(dir_path)

import importlib
import unittest


class TestSamePathPackageFacades(unittest.TestCase):
    def test_core_facades_export_expected_symbols(self) -> None:
        cases = {
            "src.core.hwp_handler": ["HwpHandler", "ConvertFormat", "ConversionResult", "OperationResult"],
            "src.core.action_runner": ["ActionRunner", "ActionCommand", "ActionPreset"],
            "src.core.doc_diff": ["DocDiff", "ChangeType", "DiffReport"],
            "src.core.template_store": ["TemplateStore", "TemplateInfo", "TemplateCategory"],
            "src.core.macro_recorder": ["MacroRecorder", "MacroAction", "datetime"],
        }

        for module_name, exports in cases.items():
            module = importlib.import_module(module_name)
            self.assertTrue(hasattr(module, "__path__"), module_name)
            for export in exports:
                self.assertTrue(hasattr(module, export), f"{module_name}.{export}")

    def test_ui_and_worker_facades_export_expected_symbols(self) -> None:
        worker = importlib.import_module("src.utils.worker")
        self.assertTrue(hasattr(worker, "__path__"))
        for export in ("ActionConsoleWorker", "DataInjectWorker", "WorkerResult", "com_context", "make_summary_data"):
            self.assertTrue(hasattr(worker, export), export)

        main_window = importlib.import_module("src.ui.main_window")
        self.assertTrue(hasattr(main_window, "__path__"))
        for export in ("MainWindow", "Sidebar", "get_settings_manager"):
            self.assertTrue(hasattr(main_window, export), export)


if __name__ == "__main__":
    unittest.main()

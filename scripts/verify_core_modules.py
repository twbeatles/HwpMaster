
import sys
import os
import traceback

# 프로젝트 루트를 sys.path에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_module(module_name):
    print(f"Testing {module_name}...")
    try:
        if module_name == 'src.core.hwp_handler':
            from src.core.hwp_handler import HwpHandler
            print(f"  [OK] {module_name} imported")
        elif module_name == 'src.core.table_doctor':
            from src.core.table_doctor import TableDoctor
            print(f"  [OK] {module_name} imported")
        elif module_name == 'src.core.watermark_manager':
            from src.core.watermark_manager import WatermarkManager
            print(f"  [OK] {module_name} imported")
        elif module_name == 'src.core.regex_replacer':
            from src.core.regex_replacer import RegexReplacer
            print(f"  [OK] {module_name} imported")
        elif module_name == 'src.core.doc_diff':
            from src.core.doc_diff import DocDiff
            print(f"  [OK] {module_name} imported")
        return True
    except Exception:
        print(f"  [FAIL] {module_name}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    modules = [
        'src.core.hwp_handler',
        'src.core.table_doctor',
        'src.core.watermark_manager',
        'src.core.regex_replacer',
        'src.core.doc_diff'
    ]
    
    failed = False
    for module in modules:
        if not test_module(module):
            failed = True
            
    if failed:
        sys.exit(1)
    else:
        print("\nAll modules verified successfully!")
        sys.exit(0)

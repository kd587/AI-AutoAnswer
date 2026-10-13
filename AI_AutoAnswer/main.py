import ctypes
import sys

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass
    app = QApplication(sys.argv)
    window = MainWindow(start_mcp=not any(flag in sys.argv for flag in
                        ("--self-test", "--self-test-ocr")))
    if "--self-test-ocr" in sys.argv:
        from app.recognition.ocr_engine import OCREngine
        OCREngine()._get_engine()
        window.close()
        return 0
    if "--self-test" in sys.argv:
        window.close()
        return 0
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

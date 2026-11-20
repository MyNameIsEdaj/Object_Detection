"""Start the Object Spotter GUI."""
import sys

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from . import theme
from .main_window import MainWindow
from .titlebar import logo_icon


def _set_windows_app_id():
    """Give the app its own taskbar entry so Windows shows our logo, not Python's icon."""
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ObjectSpotter.App")
        except Exception:
            pass


def run(model_path=None, theme_name=None):
    _set_windows_app_id()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Object Spotter")
    settings = QSettings("ObjectSpotter", "ObjectSpotter")  # remembers the last theme
    theme.load_fonts()
    name = theme.apply(theme_name or str(settings.value("theme", theme.DEFAULT_THEME)))
    settings.setValue("theme", name)
    app.setStyleSheet(theme.stylesheet())
    app.setWindowIcon(logo_icon())
    window = MainWindow(model_path) if model_path else MainWindow()
    window.fit_to_screen()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(run())

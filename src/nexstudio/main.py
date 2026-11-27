# NexStudio — NEXSTUDIO ÖZGÜR YAZILIM LİSANSI (NPL-v2), Telif Hakkı (c) 2026 Ali Mert Taşcı / NexHub. Ayrıntılar: LICENSE.txt
"""Uygulamanın giriş noktası."""
from . import state
from .classic_app import (  # noqa: F401
    NexHubApp,
)
from .core import (  # noqa: F401
    QApplication,
    QColor,
    QIcon,
    QMessageBox,
    QPalette,
    Qt,
    acquire_single_instance,
    ctypes,
    get_resource_path,
    init_ui_bridge,
    sys,
)
from .app_api import (  # noqa: F401
    notify_running_instance,
    run_ui_window_process,
)


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--ui":
        run_ui_window_process(sys.argv[2])
    try:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    except Exception:
        pass
    app = QApplication(sys.argv)
    
    try: 
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('nexhub.nexstudio.2')
    except: 
        pass
    
    app.setStyle("Fusion")
    app.setWindowIcon(QIcon(get_resource_path("app_icon.ico")))
    try:
        app_palette = app.palette()
        app_palette.setColor(QPalette.Window, QColor("#070B14"))
        app_palette.setColor(QPalette.Base, QColor("#070B14"))
        app_palette.setColor(QPalette.AlternateBase, QColor("#0B1220"))
        app_palette.setColor(QPalette.Text, QColor("#F8FAFC"))
        app_palette.setColor(QPalette.WindowText, QColor("#F8FAFC"))
        app.setPalette(app_palette)
    except Exception:
        pass
    app.setStyleSheet("QMainWindow { background-color: #070B14; } QWidget#AppRoot { background-color: #070B14; }")
    
    init_ui_bridge()
    if not acquire_single_instance():
        # Zaten açık: çalışan kopyaya "pencereni göster" de ve çık.
        if not notify_running_instance():
            QMessageBox.information(None, "NexStudio", "NexStudio zaten çalışıyor. Sağ alttaki simgeden açabilirsiniz.")
        sys.exit(0)
    state.MAIN_WINDOW = NexHubApp()
    state.MAIN_WINDOW.open_preferred_ui()
    
    sys.exit(app.exec_())

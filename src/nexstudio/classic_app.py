# NexStudio — NEXSTUDIO ÖZGÜR YAZILIM LİSANSI (NPL-v2), Telif Hakkı (c) 2026 Ali Mert Taşcı / NexHub. Ayrıntılar: LICENSE.txt

"""Ana uygulama sınıfı NexHubApp: cihaz bağlantısı, profiller, tray, klasik pencere."""
from . import state
from .core import (  # noqa: F401
    APP_ICON_PATH,
    APP_VERSION,
    AudioUtilities,
    CLSCTX_ALL,
    ERROR_LOG_FILE,
    HAS_PYCAW,
    HAS_QR,
    IAudioEndpointVolume,
    LOCALES_DIR,
    NEXHUB_YOUTUBE_CHANNEL,
    NEXSTUDIO_CHANGELOG,
    NIRCMD_PATH,
    PLUGINS_DIR,
    QAction,
    QApplication,
    QColor,
    QColorDialog,
    QComboBox,
    QDialog,
    QFileDialog,
    QFont,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QIcon,
    QImage,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPainter,
    QPalette,
    QPixmap,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QSystemTrayIcon,
    QTextEdit,
    QTimer,
    QVBoxLayout,
    QWidget,
    Qt,
    TASK_WORKER,
    comtypes,
    copy,
    ctypes,
    datetime,
    flush_pending_ui_logs,
    is_process_elevated,
    os,
    qrcode,
    re,
    relaunch_as_admin,
    release_single_instance,
    secrets,
    serial,
    string,
    subprocess,
    sys,
    time,
    ui_log,
    webbrowser,
    winreg,
    wintypes,
    write_error_log,
)
from .classic_widgets import (  # noqa: F401
    AnimatedButton,
    ChangelogHoverCard,
    ColorActionCard,
    ColorNavButton,
    HoverScaleFrame,
    ToastLabel,
    get_stylesheet,
)
from .engine import (  # noqa: F401
    DEFAULT_MOBILE_PORT,
    DEFAULT_PROFILE_NAME,
    FACTORY_DEFAULT_BUTTONS,
    NEXTION_TEXT_OBJ_BY_SLOT,
    NEXTION_TEXT_RESET_OBJS,
    TOUCH_UI_SLOT_TO_SIGNAL,
    VK_VOLUME_DOWN,
    VK_VOLUME_UP,
    apply_active_profile,
    ensure_profiles,
    execute_macro,
    find_available_port,
    format_action_details,
    format_assignment_label,
    get_all_macros,
    get_physical_buttons,
    load_config,
    load_plugins,
    press_key,
    resolve_nextion_signal,
    save_config,
    should_ignore_serial_signal,
    snapshot_profile_data,
)
from .app_api import (  # noqa: F401
    LocalAppServer,
)
from .webserver import (  # noqa: F401
    clear_all_web_sessions,
    MobileServerThread,
    WEB_ACCESS_SESSIONS,
    WEB_BLOCKED_CLIENTS,
    WEB_PIN_FAILURES,
    append_system_log,
    cleanup_old_log_files,
    get_local_ip,
)
from .serial_link import (  # noqa: F401
    SerialThread,
)
from .i18n import (  # noqa: F401
    apply_language_packs_to_core,
    load_locales,
    tr,
)

class NexHubApp(QMainWindow):
    def __init__(self):
        super().__init__()
        state.MAIN_WINDOW = self
        
        self.config = load_config()
        cleanup_old_log_files(7)
        load_locales()
        load_plugins()
        apply_language_packs_to_core()
        self.serial_thread = None
        self.mobile_thread = None
        self.current_signal = None
        self.web_sensitive_visible = False
        self._last_window_was_maximized = False
        self._normal_window_size = (1100, 750)
        self.setWindowTitle("NexStudio")
        if os.path.exists(APP_ICON_PATH):
            self.setWindowIcon(QIcon(APP_ICON_PATH))
        self.setMinimumSize(1100, 750)
        self.resize(*self._normal_window_size)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self.apply_theme()
        self._window_bg = QFrame(self)
        self._window_bg.setObjectName("WindowBackgroundLayer")
        self._window_bg.setStyleSheet("QFrame#WindowBackgroundLayer { background-color: #070B14; }")
        self._window_bg.setGeometry(self.rect())
        self._window_bg.lower()
        self.init_ui()
        self.setup_tray()
        self.encoder_pending_steps = 0
        self.encoder_flush_timer = QTimer(self)
        self.encoder_flush_timer.setSingleShot(True)
        self.encoder_flush_timer.timeout.connect(self.process_encoder_pending_steps)
        self.device_supports_hid = False
        self.device_supports_ping = False
        self.device_fw = ""
        self._user_disconnected = False
        self.reconnect_timer = QTimer(self)
        self.reconnect_timer.timeout.connect(self.try_reconnect)
        self.heartbeat_timer = QTimer(self)
        self.heartbeat_timer.timeout.connect(self.check_device_heartbeat)
        self.heartbeat_timer.start(3000)
        self.ui_process = None
        self._ui_started_at = 0.0
        import collections
        self._live_seq = 0
        self._live_events = collections.deque(maxlen=64)
        self.ui_watch_timer = QTimer(self)
        self.ui_watch_timer.timeout.connect(self.check_ui_process)
        self.local_app = LocalAppServer()
        # 2.6.4: arka planda güncelleme kontrolü (açılıştan 15 sn sonra, sonra günde bir)
        from . import updater
        updater.start_background_checks()
        if hasattr(self, "log_area"):
            self.log_area.document().setMaximumBlockCount(1500)
        flush_pending_ui_logs()
        ui_log(f"NexStudio {APP_VERSION} başlatıldı" + (" (yönetici)" if is_process_elevated() else ""))
        self.apply_startup_setting()
        QTimer.singleShot(900, self.auto_connect_device)
        if self.config.get("web_auto_start", False) or self.config.get("app_mode", "device") == "web":
            QTimer.singleShot(1300, self.auto_start_web_control)


    def paintEvent(self, event):
        # Ana pencere büyütülürken Qt'nin kısa süreli beyaz zemin göstermesini engeller.
        super().paintEvent(event)
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#070B14"))
        painter.end()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        try:
            if hasattr(self, "_window_bg") and self._window_bg:
                self._window_bg.setGeometry(self.rect())
                self._window_bg.lower()
            if self.centralWidget():
                self.centralWidget().updateGeometry()
                self.centralWidget().update()
            if hasattr(self, "stack"):
                self.stack.updateGeometry()
                self.stack.update()
        except Exception:
            pass

    def force_full_repaint(self):
        try:
            if hasattr(self, "_window_bg") and self._window_bg:
                self._window_bg.setGeometry(self.rect())
                self._window_bg.lower()
                self._window_bg.show()
            if self.centralWidget():
                self.centralWidget().updateGeometry()
                self.centralWidget().update()
            self.updateGeometry()
            self.update()
            self.repaint()
        except Exception:
            pass


    def current_accent(self):
        return self.config.get("accent_color", "#3B82F6")

    def apply_theme(self):
        self.setStyleSheet(get_stylesheet(self.current_accent()) + """
            QMainWindow { background-color: #070B14; }
            QWidget#AppRoot, QWidget#ContentRoot, QStackedWidget#MainStack, QWidget#MainPage, QWidget#PageSurface { background-color: #070B14; }
        """)
        try:
            pal = self.palette()
            pal.setColor(QPalette.Window, QColor("#070B14"))
            pal.setColor(QPalette.Base, QColor("#070B14"))
            pal.setColor(QPalette.AlternateBase, QColor("#0B1220"))
            pal.setColor(QPalette.Text, QColor("#F8FAFC"))
            pal.setColor(QPalette.WindowText, QColor("#F8FAFC"))
            self.setPalette(pal)
        except Exception:
            pass

    def refresh_dynamic_button_styles(self):
        # Renk değişince mevcut arayüzü komple yeniden kurmadan,
        # dinamik butonların rengini günceller.
        try:
            for btn in self.findChildren(AnimatedButton):
                btn.apply_default_style()
        except Exception:
            pass

        try:
            for nav in getattr(self, "nav_buttons", []):
                nav.refresh_style()
        except Exception:
            pass

    def init_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("AppRoot")
        central_widget.setAttribute(Qt.WA_StyledBackground, True)
        central_widget.setAutoFillBackground(True)
        central_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(18)

        # Modern ürün UI: sol navigasyon + üst komut alanı + büyük çalışma yüzeyi.
        self.sidebar = QWidget()
        self.sidebar.setObjectName("SideRail")
        self.sidebar.setFixedWidth(275)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(20, 22, 20, 20)
        sidebar_layout.setSpacing(10)

        brand_row = QHBoxLayout()
        logo = QLabel()
        logo.setFixedSize(44, 44)
        logo.setAlignment(Qt.AlignCenter)
        logo_pm = QPixmap(APP_ICON_PATH)
        if not logo_pm.isNull():
            logo.setPixmap(logo_pm.scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            logo.setText("N")
            logo.setStyleSheet(f"background-color: {self.current_accent()}; color: white; border-radius: 12px; font-size: 18px; font-weight: 900;")
        brand_text = QVBoxLayout()
        brand = QLabel("NexStudio")
        brand.setObjectName("BrandTitle")
        brand_sub = QLabel(tr("brand_subtitle"))
        brand_sub.setObjectName("BrandSub")
        brand_text.addWidget(brand)
        brand_text.addWidget(brand_sub)
        brand_row.addWidget(logo)
        brand_row.addLayout(brand_text)
        brand_row.addStretch()
        sidebar_layout.addLayout(brand_row)
        sidebar_layout.addSpacing(14)

        self.nav_buttons = []
        self.nav_log_button = None
        nav_items = [
            ("⌂", self.current_accent(), tr("home"), 0),
            ("⌨", "#10B981", tr("tab_physical"), 1),
            ("▣", "#8B5CF6", tr("tab_screen"), 2),
            ("☰", self.current_accent(), tr("tab_log"), 3),
            ("🌐", "#EC4899", tr("tab_web"), 5),
        ]
        for badge, color, label, index in nav_items:
            btn = ColorNavButton(badge, color, label)
            btn.page_index = index
            btn.clicked.connect(lambda i=index: self.switch_main_page(i))
            if index == 3:
                self.nav_log_button = btn
            self.nav_buttons.append(btn)
            sidebar_layout.addWidget(btn)
        self.update_system_log_nav_visibility()

        sidebar_layout.addStretch()
        self.quick_card = QWidget()
        self.quick_card.setObjectName("HeroCard")
        quick_l = QVBoxLayout(self.quick_card)
        quick_l.setContentsMargins(16, 16, 16, 16)
        quick_title = QLabel(tr("device_status"))
        quick_title.setObjectName("SectionTitle")
        self.lbl_sidebar_status = QLabel(tr("status_waiting"))
        self.lbl_sidebar_status.setObjectName("StatusPill")
        self.lbl_sidebar_status.setWordWrap(True)
        quick_l.addWidget(quick_title)
        quick_l.addWidget(self.lbl_sidebar_status)
        quick_hint = QLabel(tr("sidebar_status_hint"))
        quick_hint.setObjectName("Muted")
        quick_hint.setWordWrap(True)
        quick_l.addWidget(quick_hint)
        sidebar_layout.addWidget(self.quick_card)

        root_layout.addWidget(self.sidebar)

        content = QWidget()
        content.setObjectName("ContentRoot")
        content.setAttribute(Qt.WA_StyledBackground, True)
        content.setAutoFillBackground(True)
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)

        topbar = QWidget()
        topbar.setObjectName("Topbar")
        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(20, 16, 20, 16)
        topbar_layout.setSpacing(12)

        title_box = QVBoxLayout()
        self.lbl_page_title = QLabel(tr("home"))
        self.lbl_page_title.setObjectName("PageTitle")
        self.lbl_page_subtitle = QLabel(tr("page_sub_home"))
        self.lbl_page_subtitle.setObjectName("PageSubtitle")
        self.lbl_page_subtitle.setWordWrap(True)
        self.lbl_page_title.setMinimumWidth(0)
        self.lbl_page_subtitle.setMinimumWidth(0)
        title_box.addWidget(self.lbl_page_title)
        title_box.addWidget(self.lbl_page_subtitle)
        topbar_layout.addLayout(title_box, 1)

        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(220)
        self.refresh_ports()
        btn_refresh = QPushButton("🔄")
        btn_refresh.setObjectName("IconBtn")
        btn_refresh.setToolTip(tr("refresh"))
        btn_refresh.clicked.connect(self.refresh_ports)
        self.btn_connect = QPushButton(tr("connect"))
        self.btn_connect.setObjectName("ConnectBtn")
        self.btn_connect.clicked.connect(self.toggle_connection)

        self.btn_settings_top = QPushButton("⚙ " + tr("settings_button"))
        self.btn_settings_top.setObjectName("SettingsTopBtn")
        self.btn_settings_top.clicked.connect(lambda: self.switch_main_page(4))
        topbar_layout.addWidget(self.port_combo)
        topbar_layout.addWidget(btn_refresh)
        topbar_layout.addWidget(self.btn_connect)
        topbar_layout.addWidget(self.btn_settings_top)
        content_layout.addWidget(topbar)

        self.stack = QStackedWidget()
        self.stack.setObjectName("MainStack")
        self.stack.setAttribute(Qt.WA_StyledBackground, True)
        self.stack.setAutoFillBackground(True)
        self.stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tab_home = QWidget()
        self.tab_physical = QWidget()
        self.tab_screen = QWidget()
        self.tab_log = QWidget()
        self.tab_settings = QWidget()
        self.tab_web = QWidget()

        self.stack.addWidget(self.tab_home)
        self.stack.addWidget(self.tab_physical)
        self.stack.addWidget(self.tab_screen)
        self.stack.addWidget(self.tab_log)
        self.stack.addWidget(self.tab_settings)
        self.stack.addWidget(self.tab_web)
        content_layout.addWidget(self.stack, 1)
        self.toast = ToastLabel(self.sidebar)

        self.setup_home_tab()
        self.setup_physical_tab()
        self.setup_screen_tab()
        self.setup_log_tab()
        self.setup_settings_tab()
        self.setup_web_tab()

        root_layout.addWidget(content, 1)
        self.switch_main_page(0)
        QTimer.singleShot(0, self.force_full_repaint)

    def get_changelog_entries(self):
        lang = self.config.get("language", "tr")
        if lang in NEXSTUDIO_CHANGELOG:
            return NEXSTUDIO_CHANGELOG[lang]
        return NEXSTUDIO_CHANGELOG.get("tr", [])

    def get_changelog_hint(self):
        if self.config.get("language", "tr") == "en":
            return "Hover to expand, scroll to read every release."
        return "Üzerine gelince kart genişler; kaydırarak tüm sürümleri okuyabilirsin."

    def build_web_info_cards(self):
        if self.config.get("language", "tr") == "en":
            return {
                "overview_title": "Current Status",
                "overview_desc": "Web Control is now a mobile-friendly control panel for assignments, touch preview, wheel control, and quick actions.",
                "roadmap_title": "Available / Planned",
                "roadmap_items": [
                    "Works from a phone without requiring the physical device to be connected",
                    "Button assignment, touch preview, wheel control, and volume controls are available",
                    "Hardware synchronization and account/cloud features can be expanded later",
                ],
                "notes_title": "User Note",
                "notes_desc": "You can currently use Web Control without the physical device connected. Use your phone to assign buttons and control actions remotely; device synchronization can be added later when the hardware is connected.",
            }
        return {
            "overview_title": "Mevcut Durum",
            "overview_desc": "Web Kontrolü; atama, dokunmatik ekran önizleme, tekerlek kontrolü ve hızlı işlemler için mobil uyumlu bir kontrol panelidir.",
            "roadmap_title": "Kullanılabilir / Planlanan",
            "roadmap_items": [
                "Fiziksel cihaz bağlı olmasa bile telefondan kullanılabilir",
                "Tuş atama, dokunmatik ekran önizleme, tekerlek kontrolü ve ses işlemleri kullanılabilir",
                "Donanım eşitleme ve hesap/bulut özellikleri ileride genişletilebilir",
            ],
            "notes_title": "Kullanıcı Notu",
            "notes_desc": "Şu anda Web Kontrolü cihaz bağlı olmadan da kullanılabilir. Telefonundan tuş ataması yapabilir ve kontrolleri uzaktan çalıştırabilirsin; cihaz bağlandığında eşitleme akışı daha sonra kullanılabilir.",
        }

    def setup_home_tab(self):
        layout = QVBoxLayout(self.tab_home)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(18)

        hero = QWidget()
        hero.setObjectName("HeroCard")
        hero_l = QHBoxLayout(hero)
        hero_l.setContentsMargins(28, 26, 28, 26)
        hero_l.setSpacing(24)

        left = QVBoxLayout()
        title = QLabel(tr("home_title"))
        title.setObjectName("PageTitle")
        title.setWordWrap(True)  # 2.0: dar pencerede başlık kesilmesin
        desc = QLabel(tr("home_desc"))
        desc.setObjectName("PageSubtitle")
        desc.setWordWrap(True)
        left.addWidget(title)
        left.addWidget(desc)
        # 2.0: Dar pencerede yan yana sığmayıp yazıları kesiliyordu; alt alta yerleşir.
        btn_row = QVBoxLayout()
        btn_row.setSpacing(10)
        btn_physical = AnimatedButton(tr("edit_physical_keys"), accent="#EF4444")
        btn_physical.setObjectName("SaveBtn")
        btn_physical.setHoverHeights(52, 7)
        btn_physical.clicked.connect(lambda: self.switch_main_page(1))
        btn_screen = AnimatedButton(tr("screen_pages"), accent=self.config.get("accent_color", "#3B82F6"))
        btn_screen.setHoverHeights(52, 7)
        btn_screen.clicked.connect(lambda: self.switch_main_page(2))
        btn_row.addWidget(btn_physical)
        btn_row.addWidget(btn_screen)
        left.addSpacing(12)
        left.addLayout(btn_row)
        left.addStretch()
        hero_l.addLayout(left, 1)

        device_card = ChangelogHoverCard(
            tr("quick_status"),
            self.get_changelog_hint(),
            self.get_changelog_entries()
        )
        hero_l.addWidget(device_card)
        layout.addWidget(hero)

        cards = QHBoxLayout()
        cards.setSpacing(16)
        card_specs = [
            ("⌨", "#10B981", tr("tab_physical"), tr("card_phys_desc"), 1),
            ("▣", "#8B5CF6", tr("tab_screen"), tr("card_screen_desc"), 2),
            ("◉", "#F59E0B", tr("wheel_label"), tr("card_encoder_desc"), 1),
            ("🌐", "#EC4899", tr("tab_web"), tr("page_sub_web"), 5),
        ]
        for badge, color, title, desc, page in card_specs:
            card = ColorActionCard(badge, color, title, desc)
            card.clicked.connect(lambda i=page: self.switch_main_page(i))
            cards.addWidget(card)
        layout.addLayout(cards)
        layout.addStretch()

    def switch_main_page(self, index):
        self.stack.setCurrentIndex(index)
        page_titles = [
            tr("home"),
            tr("tab_physical"),
            tr("tab_screen"),
            tr("tab_log"),
            tr("tab_settings"),
            tr("tab_web"),
        ]
        page_subtitles = [
            tr("page_sub_home"),
            tr("page_sub_physical"),
            tr("page_sub_screen"),
            tr("page_sub_log"),
            tr("page_sub_settings"),
            tr("page_sub_web"),
        ]
        if hasattr(self, "lbl_page_title"):
            self.lbl_page_title.setText(page_titles[index])
            self.lbl_page_subtitle.setText(page_subtitles[index])
        for btn in getattr(self, "nav_buttons", []):
            btn.setChecked(getattr(btn, "page_index", -1) == index)

    def update_system_log_nav_visibility(self):
        try:
            visible = bool(self.config.get("show_system_log_menu", False))
            if hasattr(self, "nav_log_button") and self.nav_log_button:
                self.nav_log_button.setVisible(visible)
        except Exception:
            pass

    def open_system_log_from_settings(self):
        self.switch_main_page(3)

    def toggle_system_log_menu(self):
        self.config["show_system_log_menu"] = not self.config.get("show_system_log_menu", False)
        save_config(self.config)
        self.update_system_log_nav_visibility()
        if hasattr(self, "btn_log_visibility"):
            self.btn_log_visibility.setText(("✅ " if self.config.get("show_system_log_menu", False) else "❌ ") + "Sistem Günlüğü sol menüde görünsün")
        if not self.config.get("show_system_log_menu", False) and hasattr(self, "stack") and self.stack.currentIndex() == 3:
            self.switch_main_page(4)
        self.show_saved_feedback(tr("saved_short"))


    def clear_system_log(self):
        try:
            if hasattr(self, "log_area"):
                self.log_area.clear()
            append_system_log("🧹 Sistem Günlüğü temizlendi.")
            self.show_saved_feedback("Günlük temizlendi")
        except Exception:
            pass

    def export_system_log(self):
        try:
            default_name = f"nexstudio_log_export_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.txt"
            path, _ = QFileDialog.getSaveFileName(self, "Sistem Günlüğünü Dışa Aktar", os.path.join(os.path.expanduser("~"), default_name), "Metin Dosyası (*.txt)")
            if not path:
                return
            if not path.lower().endswith(".txt"):
                path += ".txt"
            content = self.log_area.toPlainText() if hasattr(self, "log_area") else ""
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.show_saved_feedback("Günlük dışa aktarıldı")
        except Exception as e:
            QMessageBox.warning(self, "Sistem Günlüğü", f"Günlük dışa aktarılamadı:\n{e}")

    def toggle_web_history_panel(self):
        if not hasattr(self, "list_web_history"):
            return
        visible = not self.list_web_history.isVisible()
        self.list_web_history.setVisible(visible)
        if hasattr(self, "btn_history_toggle"):
            self.btn_history_toggle.setText("🙈 Web Giriş Geçmişini Gizle" if visible else "📜 Web Giriş Geçmişini Göster")
        if visible:
            self.refresh_web_history_list()

    def refresh_web_history_list(self):
        try:
            if not hasattr(self, "list_web_history"):
                return
            self.list_web_history.clear()
            for entry in self.config.get("web_access_history", [])[:120]:
                if not isinstance(entry, dict):
                    continue
                device_name = entry.get("device_name") or "Bilinmeyen cihaz"
                line = f"{entry.get('time','')} | {entry.get('event','')} | {device_name} | {entry.get('ip_display', entry.get('ip',''))} | {entry.get('device_type','')} / {entry.get('os_name','')} / {entry.get('browser','')}"
                detail = entry.get("detail", "")
                if detail:
                    line += f" | {detail}"
                item = QListWidgetItem(line)
                item.setData(Qt.UserRole, entry.get("device_id", ""))
                self.list_web_history.addItem(item)
        except Exception:
            pass

    def refresh_known_devices_combo(self):
        try:
            if not hasattr(self, "combo_known_devices"):
                return
            current = self.combo_known_devices.currentData()
            self.combo_known_devices.blockSignals(True)
            self.combo_known_devices.clear()
            known = self.config.get("known_web_devices", {})
            if isinstance(known, dict) and known:
                for device_id, data in sorted(known.items(), key=lambda item: item[1].get("last_seen", ""), reverse=True):
                    name = data.get("name", "Tanınan cihaz")
                    desc = f"{data.get('device_type','')} / {data.get('os_name','')} / {data.get('browser','')}"
                    self.combo_known_devices.addItem(f"{name} — {desc}", device_id)
            else:
                self.combo_known_devices.addItem("Henüz tanınan cihaz yok", "")
            if current:
                idx = self.combo_known_devices.findData(current)
                if idx >= 0:
                    self.combo_known_devices.setCurrentIndex(idx)
            self.combo_known_devices.blockSignals(False)
        except Exception:
            pass

    def refresh_web_security_panel(self):
        try:
            self.config = state.APP_CONFIG
            if hasattr(self, "btn_web_auto_start"):
                self.btn_web_auto_start.setText(("✅ " if self.config.get("web_auto_start", False) else "❌ ") + "Uygulama açılınca Web Kontrolü otomatik başlasın")
            if hasattr(self, "btn_web_private_log"):
                self.btn_web_private_log.setText(("✅ " if self.config.get("web_private_log", False) else "❌ ") + "Günlükte IP adreslerini gizle")
            if hasattr(self, "btn_web_known_only"):
                self.btn_web_known_only.setText(("✅ " if self.config.get("web_known_only", False) else "❌ ") + "Sadece tanınan cihazlar Web Kontrolü kullanabilsin")
            self.refresh_known_devices_combo()
            self.refresh_web_history_list()
            if hasattr(self, "lbl_settings_last_device"):
                history = self.config.get("web_access_history", []) if isinstance(self.config.get("web_access_history", []), list) else []
                last = history[0] if history else {}
                if isinstance(last, dict) and last:
                    self.lbl_settings_last_device.setText(
                        f"Son bağlantı: {last.get('device_name', '-')} • {last.get('time', '-')}\n"
                        f"Cihaz: {last.get('device_type', '-')} / {last.get('browser', '-')} • IP: {last.get('ip_display', last.get('ip', '-'))}"
                    )
                else:
                    self.lbl_settings_last_device.setText("Son bağlantı: -")
            if hasattr(self, "refresh_web_control_status"):
                self.refresh_web_control_status()
        except Exception:
            pass

    def toggle_web_auto_start(self):
        self.config["web_auto_start"] = not self.config.get("web_auto_start", False)
        save_config(self.config)
        self.refresh_web_security_panel()
        self.show_saved_feedback(tr("saved_short"))

    def toggle_web_private_log(self):
        self.config["web_private_log"] = not self.config.get("web_private_log", False)
        save_config(self.config)
        self.refresh_web_security_panel()
        self.show_saved_feedback(tr("saved_short"))

    def toggle_web_known_only(self):
        self.config["web_known_only"] = not self.config.get("web_known_only", False)
        save_config(self.config)
        self.refresh_web_security_panel()
        self.show_saved_feedback(tr("saved_short"))

    def regenerate_web_pin(self):
        try:
            alphabet = string.ascii_uppercase + string.digits
            new_pin = ''.join(secrets.choice(alphabet) for _ in range(6))
            self.config["mobile_pin"] = new_pin
            save_config(self.config)
            if hasattr(self, "lbl_mobile_ip") and self.mobile_thread and self.mobile_thread.is_running:
                self.lbl_mobile_ip.setText(f"PIN: {new_pin}")
            self.refresh_web_control_status()
            append_system_log("🔐 Web Kontrolü PIN kodu yenilendi.")
            self.show_saved_feedback("PIN yenilendi")
        except Exception as e:
            QMessageBox.warning(self, "Web Güvenliği", f"PIN yenilenemedi:\n{e}")

    def reset_web_sessions(self):
        try:
            alphabet = string.ascii_uppercase + string.digits
            self.config["mobile_pin"] = ''.join(secrets.choice(alphabet) for _ in range(6))
            self.config["web_token"] = secrets.token_urlsafe(8)
            WEB_ACCESS_SESSIONS.clear()
            clear_all_web_sessions()
            WEB_PIN_FAILURES.clear()
            WEB_BLOCKED_CLIENTS.clear()
            save_config(self.config)
            self.update_current_web_url_after_token_change()
            self.refresh_web_control_status()
            append_system_log("🔁 Web oturumları sıfırlandı; QR/link ve PIN yenilendi. Tanınan cihaz kayıtları korunur.")
            self.show_saved_feedback("QR / link yenilendi")
        except Exception as e:
            QMessageBox.warning(self, "Web Güvenliği", f"Oturumlar sıfırlanamadı:\n{e}")

    def update_current_web_url_after_token_change(self):
        try:
            if self.mobile_thread and self.mobile_thread.is_running:
                ip = get_local_ip()
                port = self.current_mobile_port or self.config.get("last_mobile_port", DEFAULT_MOBILE_PORT)
                url = f"http://{ip}:{port}/{self.config.get('web_token', '')}"
                self.current_web_url = url
                if hasattr(self, "lbl_mobile_ip"):
                    self.lbl_mobile_ip.setText(f"PIN: {self.config.get('mobile_pin','')}")
                if hasattr(self, "lbl_web_url"):
                    self.lbl_web_url.setText(url)
                if HAS_QR and hasattr(self, "lbl_qr_image"):
                    qr = qrcode.QRCode(version=1, box_size=4, border=4)
                    qr.add_data(url)
                    qr.make(fit=True)
                    img = qr.make_image(fill_color="black", back_color="white")
                    img = img.convert("RGBA")
                    data = img.tobytes("raw", "RGBA")
                    qim = QImage(data, img.size[0], img.size[1], QImage.Format_RGBA8888)
                    self.lbl_qr_image.setPixmap(QPixmap.fromImage(qim))
                self.refresh_web_control_status()
        except Exception:
            pass

    def rename_known_device(self):
        try:
            if not hasattr(self, "combo_known_devices"):
                return
            device_id = self.combo_known_devices.currentData()
            if not device_id:
                QMessageBox.information(self, "Tanınan Cihazlar", "Henüz adlandırılacak cihaz yok.")
                return
            known = self.config.get("known_web_devices", {})
            current_name = known.get(device_id, {}).get("name", "Tanınan cihaz")
            new_name, ok = QInputDialog.getText(self, "Cihazı Adlandır", "Bu cihaz için görünen ad:", text=current_name)
            if ok and new_name.strip():
                known[device_id]["name"] = new_name.strip()
                self.config["known_web_devices"] = known
                save_config(self.config)
                self.refresh_web_security_panel()
                self.show_saved_feedback("Cihaz adı kaydedildi")
        except Exception as e:
            QMessageBox.warning(self, "Tanınan Cihazlar", f"Cihaz adı değiştirilemedi:\n{e}")

    def forget_known_device(self):
        try:
            device_id = self.combo_known_devices.currentData() if hasattr(self, "combo_known_devices") else ""
            if not device_id:
                return
            known = self.config.get("known_web_devices", {})
            name = known.get(device_id, {}).get("name", "Bu cihaz")
            reply = QMessageBox.question(self, "Cihazı Unut", f"'{name}' tanınan cihaz listesinden kaldırılsın mı?", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                known.pop(device_id, None)
                self.config["known_web_devices"] = known
                save_config(self.config)
                self.refresh_web_security_panel()
                self.show_saved_feedback("Cihaz unutuldu")
        except Exception:
            pass

    def auto_start_web_control(self):
        try:
            if not self.mobile_thread or not self.mobile_thread.is_running:
                self.toggle_mobile_server()
        except Exception:
            pass


    def setup_physical_tab(self):
        layout = QHBoxLayout(self.tab_physical)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(16)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(10)

        left_panel = QWidget()
        left_panel.setObjectName("GlassCard")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(18, 18, 18, 18)
        left_layout.setSpacing(12)

        title = QLabel(tr("device_keys"))
        title.setObjectName("SectionTitle")
        hint = QLabel(tr("device_keys_hint"))
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        left_layout.addWidget(title)
        left_layout.addWidget(hint)

        self.list_widget = QListWidget()
        self.list_widget.setMinimumWidth(280)
        self.list_widget.itemClicked.connect(self.on_item_clicked)

        phys_btns = get_physical_buttons()
        for sig, name in phys_btns.items():
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, sig)
            self.list_widget.addItem(item)

        left_layout.addWidget(self.list_widget)
        splitter.addWidget(left_panel)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self.right_panel = QWidget()
        self.right_panel.setObjectName("GlassCard")
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(24, 24, 24, 24)
        self.right_layout.setSpacing(14)

        self.lbl_selected_btn = QLabel(tr("select_key"))
        self.lbl_selected_btn.setObjectName("PageTitle")
        self.right_layout.addWidget(self.lbl_selected_btn)

        self.lbl_current_assignment = QLabel(f"{tr('current_assign')} {tr('empty')}")
        self.lbl_current_assignment.setObjectName("StatusPill")
        self.right_layout.addWidget(self.lbl_current_assignment)

        assign_group = QGroupBox(tr("assign_task"))
        assign_layout = QVBoxLayout(assign_group)
        assign_layout.setSpacing(10)

        assign_layout.addWidget(QLabel(tr("category")))
        self.combo_category = QComboBox()
        self.combo_category.currentIndexChanged.connect(self.update_action_combo)
        assign_layout.addWidget(self.combo_category)

        assign_layout.addWidget(QLabel(tr("task")))
        self.combo_action = QComboBox()
        self.combo_action.currentIndexChanged.connect(self.check_custom_input_phys)
        assign_layout.addWidget(self.combo_action)

        self.combo_browser_phys = QComboBox()
        self.combo_browser_phys.addItems([tr("browser_def"), tr("browser_chr"), tr("browser_edg"), tr("browser_fir")])
        self.combo_browser_phys.setVisible(False)
        assign_layout.addWidget(self.combo_browser_phys)

        self.combo_app_act_phys = QComboBox()
        self.combo_app_act_phys.addItems([tr("app_open"), tr("app_close"), tr("app_force")])
        self.combo_app_act_phys.setVisible(False)
        assign_layout.addWidget(self.combo_app_act_phys)

        app_layout = QHBoxLayout()
        self.input_phys_custom = QLineEdit()
        self.input_phys_custom.setVisible(False)
        app_layout.addWidget(self.input_phys_custom)
        self.btn_scan_apps_phys = AnimatedButton(tr("scan_apps"))
        self.btn_scan_apps_phys.setHoverHeights(42, 5)
        self.btn_scan_apps_phys.setVisible(False)
        self.btn_scan_apps_phys.clicked.connect(lambda: self.scan_installed_apps(self.input_phys_custom))
        app_layout.addWidget(self.btn_scan_apps_phys)
        assign_layout.addLayout(app_layout)
        self.right_layout.addWidget(assign_group)

        all_macros = get_all_macros()
        self.combo_category.addItems(all_macros.keys())

        self.encoder_inline_group = QGroupBox(tr("turn_func"))
        encoder_inline_layout = QVBoxLayout(self.encoder_inline_group)
        encoder_inline_layout.setSpacing(10)
        self.lbl_encoder_inline_hint = QLabel(tr("encoder_hint"))
        self.lbl_encoder_inline_hint.setObjectName("Muted")
        self.combo_encoder_turn_phys = QComboBox()
        self.combo_encoder_turn_phys.currentIndexChanged.connect(self.save_encoder_setting_from_physical)
        encoder_inline_layout.addWidget(self.lbl_encoder_inline_hint)
        encoder_inline_layout.addWidget(self.combo_encoder_turn_phys)
        self.btn_refresh_audio_apps_phys = AnimatedButton(tr("refresh_audio_apps"))
        self.btn_refresh_audio_apps_phys.setHoverHeights(42, 5)
        self.btn_refresh_audio_apps_phys.clicked.connect(self.refresh_audio_app_combos)
        encoder_inline_layout.addWidget(self.btn_refresh_audio_apps_phys)
        self.encoder_inline_group.setVisible(False)
        self.right_layout.addWidget(self.encoder_inline_group)
        self.refresh_audio_app_combos()

        self.right_layout.addStretch()

        btn_save = AnimatedButton("💾 " + tr("save_key").replace("💾 ", ""))
        btn_save.setHoverHeights(50, 6)
        btn_save.setObjectName("SaveBtn")
        btn_save.clicked.connect(self.save_physical_macro)
        self.right_layout.addWidget(btn_save)

        self.right_panel.setEnabled(False)
        scroll.setWidget(self.right_panel)
        splitter.addWidget(scroll)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)

    def show_saved_feedback(self, message=None):
        msg = message or tr("saved_short")
        if hasattr(self, "toast"):
            self.toast.show_message(f"✓ {msg}")
            self.position_saved_toast()
        elif hasattr(self, "log_area"):
            ui_log(f"✓ {msg}")

    def position_saved_toast(self):
        if not hasattr(self, "toast") or not hasattr(self, "quick_card"):
            return
        try:
            # Cihaz Durumu kartının hemen üstüne, sidebar içinde ortalı yerleştir.
            card_geo = self.quick_card.geometry()
            x = int((self.sidebar.width() - self.toast.width()) / 2)
            y = card_geo.y() - self.toast.height() - 10
            if y < 12:
                y = card_geo.y() + 12
            self.toast.move(max(12, x), max(12, y))
            self.toast.raise_()
        except Exception:
            pass

    def scan_installed_apps(self, target_input):
        paths = [os.path.join(os.environ["PROGRAMDATA"], "Microsoft", "Windows", "Start Menu", "Programs"), os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs")]
        apps = {}
        for path in paths:
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.endswith(".lnk"): apps[file[:-4]] = os.path.join(root, file)
        if not apps:
            QMessageBox.warning(self, tr("error"), tr("no_installed_app"))
            return
        app_names = sorted(list(apps.keys()))
        item, ok = QInputDialog.getItem(self, tr("select_app"), tr("select_app_prompt"), app_names, 0, False)
        if ok and item: target_input.setText(apps[item])

    def on_item_clicked(self, item):
        self.current_signal = item.data(Qt.UserRole)
        phys_btns = get_physical_buttons()
        self.lbl_selected_btn.setText(f"{phys_btns[self.current_signal]}")
        self.right_panel.setEnabled(True)
        cfg = self.config.get("buttons", {}).get(self.current_signal, {})
        self.lbl_current_assignment.setText(f"{tr('current_assign')} {format_assignment_label(cfg) if cfg else tr('empty')}")
        if cfg.get("action"):
            act = cfg["action"]
            if act.get("type") in ["custom_web", "web"]:
                idx = self.combo_browser_phys.findData(act.get("browser", "default"))
                if idx >= 0: self.combo_browser_phys.setCurrentIndex(idx)
            if act.get("type") == "custom_app":
                idx = self.combo_app_act_phys.findData(act.get("app_action", "open"))
                if idx >= 0: self.combo_app_act_phys.setCurrentIndex(idx)

        # Sadece Tekerlek Butonu seçiliyken çevirme işlevi ayarını göster.
        if hasattr(self, "encoder_inline_group"):
            self.encoder_inline_group.setVisible(self.current_signal == "ENC:BTN")
            if self.current_signal == "ENC:BTN" and hasattr(self, "combo_encoder_turn_phys"):
                current_turn = self.config.get("encoder", {}).get("turn", "general_volume")
                idx = self.combo_encoder_turn_phys.findData(current_turn)
                if idx >= 0:
                    self.combo_encoder_turn_phys.blockSignals(True)
                    self.combo_encoder_turn_phys.setCurrentIndex(idx)
                    self.combo_encoder_turn_phys.blockSignals(False)

    def update_action_combo(self):
        self.combo_action.clear()
        cat = self.combo_category.currentText()
        all_macros = get_all_macros()
        if cat in all_macros:
            for name, data in all_macros[cat].items(): self.combo_action.addItem(name, data)

    def check_custom_input_phys(self):
        action_data = self.combo_action.currentData()
        self.combo_browser_phys.setVisible(False)
        self.combo_app_act_phys.setVisible(False)
        self.btn_scan_apps_phys.setVisible(False)
        if action_data and action_data.get("type") == "custom_web":
            self.input_phys_custom.setVisible(True); self.input_phys_custom.setPlaceholderText(tr("placeholder_web")); self.combo_browser_phys.setVisible(True)
        elif action_data and action_data.get("type") == "custom_app":
            self.input_phys_custom.setVisible(True); self.input_phys_custom.setPlaceholderText(tr("placeholder_app")); self.combo_app_act_phys.setVisible(True); self.btn_scan_apps_phys.setVisible(True)
        elif action_data and action_data.get("type") == "custom_hotkey":
            self.input_phys_custom.setVisible(True); self.input_phys_custom.setPlaceholderText(tr("placeholder_shortcut"))
        elif action_data and action_data.get("type") == "type_text":
            self.input_phys_custom.setVisible(True); self.input_phys_custom.setPlaceholderText(tr("placeholder_type_text"))
        elif action_data and action_data.get("type") == "web":
            self.input_phys_custom.setVisible(False); self.combo_browser_phys.setVisible(True)
        else: self.input_phys_custom.setVisible(False)

    def save_physical_macro(self):
        if not self.current_signal: return
        action_data = self.combo_action.currentData()
        if action_data: action_data = action_data.copy()
        action_name = self.combo_action.currentText()
        if action_data and action_data.get("type") in ["custom_web", "custom_app", "custom_hotkey", "type_text"]: action_data["custom_arg"] = self.input_phys_custom.text().strip()
        if action_data and action_data.get("type") in ["custom_web", "web"]: action_data["browser"] = ["default", "chrome", "edge", "firefox"][self.combo_browser_phys.currentIndex()]
        if action_data and action_data.get("type") == "custom_app": action_data["app_action"] = ["open", "close", "force_close"][self.combo_app_act_phys.currentIndex()]
        if "buttons" not in self.config: self.config["buttons"] = {}
        self.config["buttons"][self.current_signal] = {
            "name": action_name,
            "action": action_data,
            "details": format_action_details(action_data)
        }
        save_config(self.config)
        self.lbl_current_assignment.setText(f"{tr('current_assign')} {format_assignment_label(self.config['buttons'][self.current_signal])}")
        self.show_saved_feedback()

    def setup_screen_tab(self):
        layout = QHBoxLayout(self.tab_screen)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(16)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(10)

        left_widget = QWidget()
        left_widget.setObjectName("GlassCard")
        left_l = QVBoxLayout(left_widget)
        left_l.setContentsMargins(22, 22, 22, 22)
        left_l.setSpacing(16)

        top_layout = QHBoxLayout()
        page_box = QVBoxLayout()
        lbl_page = QLabel(tr("screen_page_title"))
        lbl_page.setObjectName("SectionTitle")
        self.combo_page = QComboBox()
        self.update_page_combo()
        self.combo_page.currentIndexChanged.connect(self.refresh_screen_buttons)
        page_box.addWidget(lbl_page)
        page_box.addWidget(self.combo_page)
        top_layout.addLayout(page_box)
        top_layout.addStretch()
        btn_edit_page = QPushButton("✏️")
        btn_edit_page.setObjectName("IconBtn")
        btn_edit_page.clicked.connect(self.edit_page_name)
        top_layout.addWidget(btn_edit_page)
        btn_bg = QPushButton("▧ " + tr("background"))
        btn_bg.clicked.connect(self.choose_screen_bg)
        top_layout.addWidget(btn_bg)
        left_l.addLayout(top_layout)

        device_shell = QFrame()
        device_shell.setObjectName("GlassCard")
        shell_l = QVBoxLayout(device_shell)
        shell_l.setContentsMargins(18, 18, 18, 18)
        shell_l.setSpacing(10)

        shell_header = QHBoxLayout()
        shell_header.addWidget(QLabel(tr("display_preview")))
        shell_header.addStretch()
        dot1 = QLabel("●")
        dot1.setStyleSheet("color: #EF4444; background: transparent;")
        dot2 = QLabel("●")
        dot2.setStyleSheet("color: #F59E0B; background: transparent;")
        dot3 = QLabel("●")
        dot3.setStyleSheet("color: #22C55E; background: transparent;")
        shell_header.addWidget(dot1); shell_header.addWidget(dot2); shell_header.addWidget(dot3)
        shell_l.addLayout(shell_header)

        self.screen_frame = QFrame()
        self.screen_frame.setObjectName("ScreenFrame")
        self.screen_frame.setFixedSize(540, 306)
        self.update_screen_bg()
        self.screen_layout = QGridLayout(self.screen_frame)
        self.screen_layout.setContentsMargins(22, 22, 22, 22)
        self.screen_layout.setSpacing(14)
        self.screen_btns = []
        for i in range(8):
            btn = QPushButton(tr("button_label").format(i+1))
            btn.setObjectName("ScreenBtn")
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.clicked.connect(lambda checked, idx=i: self.on_screen_btn_clicked(idx))
            self.screen_layout.addWidget(btn, i // 4, i % 4)
            self.screen_btns.append(btn)

        shell_l.addWidget(self.screen_frame, alignment=Qt.AlignCenter)
        left_l.addWidget(device_shell, alignment=Qt.AlignCenter)
        left_l.addStretch()
        splitter.addWidget(left_widget)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self.screen_macro_panel = QWidget()
        self.screen_macro_panel.setObjectName("GlassCard")
        smp_layout = QVBoxLayout(self.screen_macro_panel)
        smp_layout.setContentsMargins(24, 24, 24, 24)
        smp_layout.setSpacing(12)

        self.lbl_screen_selected = QLabel(f"{tr('screen_selected')} Yok")
        self.lbl_screen_selected.setObjectName("PageTitle")
        smp_layout.addWidget(self.lbl_screen_selected)

        text_group = QGroupBox(tr("button_appearance"))
        text_group_l = QVBoxLayout(text_group)
        text_group_l.addWidget(QLabel(tr("screen_text")))
        self.input_btn_text = QLineEdit()
        self.input_btn_text.setMaxLength(15)
        text_group_l.addWidget(self.input_btn_text)
        smp_layout.addWidget(text_group)

        action_group = QGroupBox(tr("assign_task"))
        ag_l = QVBoxLayout(action_group)
        ag_l.addWidget(QLabel(tr("category")))
        self.combo_screen_cat = QComboBox()
        self.combo_screen_cat.currentIndexChanged.connect(self.update_screen_action_combo)
        ag_l.addWidget(self.combo_screen_cat)
        ag_l.addWidget(QLabel(tr("task")))
        self.combo_screen_act = QComboBox()
        self.combo_screen_act.currentIndexChanged.connect(self.check_custom_input_screen)
        ag_l.addWidget(self.combo_screen_act)

        self.combo_browser_scr = QComboBox()
        self.combo_browser_scr.addItems([tr("browser_def"), tr("browser_chr"), tr("browser_edg"), tr("browser_fir")])
        self.combo_browser_scr.setVisible(False)
        ag_l.addWidget(self.combo_browser_scr)

        self.combo_app_act_scr = QComboBox()
        self.combo_app_act_scr.addItems([tr("app_open"), tr("app_close"), tr("app_force")])
        self.combo_app_act_scr.setVisible(False)
        ag_l.addWidget(self.combo_app_act_scr)

        app_layout = QHBoxLayout()
        self.input_screen_custom = QLineEdit()
        self.input_screen_custom.setVisible(False)
        app_layout.addWidget(self.input_screen_custom)
        self.btn_scan_apps_scr = AnimatedButton(tr("scan_apps"))
        self.btn_scan_apps_scr.setHoverHeights(42, 5)
        self.btn_scan_apps_scr.setVisible(False)
        self.btn_scan_apps_scr.clicked.connect(lambda: self.scan_installed_apps(self.input_screen_custom))
        app_layout.addWidget(self.btn_scan_apps_scr)
        ag_l.addLayout(app_layout)
        smp_layout.addWidget(action_group)

        all_macros = get_all_macros()
        self.combo_screen_cat.addItems([tr("no_action")] + list(all_macros.keys()))
        smp_layout.addStretch()
        btn_save_screen = AnimatedButton(tr("save_screen"))
        btn_save_screen.setHoverHeights(50, 6)
        btn_save_screen.setObjectName("SaveBtn")
        btn_save_screen.clicked.connect(self.save_screen_macro)
        smp_layout.addWidget(btn_save_screen)

        self.screen_macro_panel.setEnabled(False)
        scroll.setWidget(self.screen_macro_panel)
        splitter.addWidget(scroll)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)
        self.refresh_screen_buttons()

    def update_page_combo(self):
        self.combo_page.clear()
        pnames = self.config.get("page_names", {})
        self.combo_page.addItem(f"{tr('page_label').format(1)} ({(pnames.get('1') or tr('page_1'))})")
        self.combo_page.addItem(f"{tr('page_label').format(2)} ({(pnames.get('2') or tr('page_2'))})")
        self.combo_page.addItem(f"{tr('page_label').format(3)} ({(pnames.get('3') or tr('page_3'))})")
        self.combo_page.addItem(f"{tr('page_label').format(4)} ({(pnames.get('4') or tr('page_4'))})")

    def edit_page_name(self):
        page_idx = self.combo_page.currentIndex() + 1
        current_name = self.config.get("page_names", {}).get(str(page_idx), "")
        new_name, ok = QInputDialog.getText(self, tr("edit_page_name"), tr("prompt_page_name"), QLineEdit.Normal, current_name)
        if ok:
            if "page_names" not in self.config: self.config["page_names"] = {}
            self.config["page_names"][str(page_idx)] = new_name
            save_config(self.config)
            self.update_page_combo()
            self.combo_page.setCurrentIndex(page_idx - 1)

    def choose_screen_bg(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("choose_bg"), "", tr("image_files"))
        if path:
            self.config["screen_bg"] = path
            save_config(self.config)
            self.update_screen_bg()

    def update_screen_bg(self):
        bg_path = self.config.get("screen_bg", "")
        if bg_path and os.path.exists(bg_path):
            bg_path = bg_path.replace("\\", "/")
            self.screen_frame.setStyleSheet(f"QFrame#ScreenFrame {{ border-image: url({bg_path}) 0 0 0 0 stretch stretch; border: 8px solid #070B14; border-radius: 28px; }}")
        else:
            self.screen_frame.setStyleSheet("QFrame#ScreenFrame { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #78ffd6, stop:1 #007991); border: 8px solid #070B14; border-radius: 28px; }")

    def update_screen_action_combo(self):
        self.combo_screen_act.clear()
        cat = self.combo_screen_cat.currentText()
        if cat == tr("no_action"): return
        all_macros = get_all_macros()
        if cat in all_macros:
            for name, data in all_macros[cat].items(): self.combo_screen_act.addItem(name, data)

    def check_custom_input_screen(self):
        action_data = self.combo_screen_act.currentData()
        self.combo_browser_scr.setVisible(False)
        self.combo_app_act_scr.setVisible(False)
        self.btn_scan_apps_scr.setVisible(False)
        if action_data and action_data.get("type") == "custom_web":
            self.input_screen_custom.setVisible(True); self.input_screen_custom.setPlaceholderText(tr("placeholder_web")); self.combo_browser_scr.setVisible(True)
        elif action_data and action_data.get("type") == "custom_app":
            self.input_screen_custom.setVisible(True); self.input_screen_custom.setPlaceholderText(tr("placeholder_app")); self.combo_app_act_scr.setVisible(True); self.btn_scan_apps_scr.setVisible(True)
        elif action_data and action_data.get("type") == "custom_hotkey":
            self.input_screen_custom.setVisible(True); self.input_screen_custom.setPlaceholderText(tr("placeholder_shortcut"))
        elif action_data and action_data.get("type") == "type_text":
            self.input_screen_custom.setVisible(True); self.input_screen_custom.setPlaceholderText(tr("placeholder_type_text"))
        elif action_data and action_data.get("type") == "web":
            self.input_screen_custom.setVisible(False); self.combo_browser_scr.setVisible(True)
        else: self.input_screen_custom.setVisible(False)

    def refresh_screen_buttons(self):
        page = self.combo_page.currentIndex() + 1
        signal_map = TOUCH_UI_SLOT_TO_SIGNAL.get(page, {})
        for i, btn in enumerate(self.screen_btns):
            # Gezinti tuşları görev almaz.
            if page == 1 and i == 7:
                btn.setText(tr("btn_next"))
                btn.setStyleSheet("background-color: #1E293B; color: #64748B;")
                continue
            elif page in [2, 3, 4] and i == 4:
                btn.setText(tr("btn_prev"))
                btn.setStyleSheet("background-color: #1E293B; color: #64748B;")
                continue
            elif page in [2, 3, 4] and i == 7:
                btn.setText(tr("btn_next") if page != 4 else "—")
                btn.setStyleSheet("background-color: #1E293B; color: #64748B;")
                continue

            btn.setStyleSheet("")
            sig = signal_map.get(i)
            if not sig:
                btn.setText("—")
                btn.setEnabled(False)
                continue

            btn.setEnabled(True)
            cfg = self.config.get("buttons", {}).get(sig, {})
            display_name = cfg.get("name", tr("empty"))
            details = cfg.get("details") or format_action_details(cfg.get("action", {}))
            detail_line = f"\n{details[:28]}" if details else ""
            if page >= 3 and cfg.get("btn_text"):
                btn.setText(f"{cfg.get('btn_text')}\n({display_name}){detail_line}")
            else:
                btn.setText(f"{tr('button_label').format(len([x for x in signal_map if x <= i]))}\n({display_name}){detail_line}")


    def on_screen_btn_clicked(self, idx):
        page = self.combo_page.currentIndex() + 1

        # Gezinti tuşları.
        if page == 1 and idx == 7:
            self.combo_page.setCurrentIndex(1)
            return
        if page in [2, 3, 4] and idx == 4:
            self.combo_page.setCurrentIndex(page - 2)
            return
        if page in [2, 3] and idx == 7:
            self.combo_page.setCurrentIndex(page)
            return
        if page == 4 and idx == 7:
            return

        signal_map = TOUCH_UI_SLOT_TO_SIGNAL.get(page, {})
        sig = signal_map.get(idx)
        if not sig:
            self.show_saved_feedback("Bu tuş sayfa geçişi için ayrılmış")
            return

        self.current_screen_signal = sig
        visual_no = len([x for x in signal_map if x <= idx])
        self.current_screen_slot_index = idx
        self.lbl_screen_selected.setText(f"{tr('screen_selected')} {tr('page_label').format(page)} - {tr('button_label').format(visual_no)}")

        cfg = self.config.get("buttons", {}).get(self.current_screen_signal, {})
        self.input_btn_text.setText(cfg.get("btn_text", ""))

        if page < 3:
            self.input_btn_text.setEnabled(False)
            self.input_btn_text.setPlaceholderText(tr("placeholder_readonly"))
        else:
            self.input_btn_text.setEnabled(True)
            self.input_btn_text.setPlaceholderText(tr("placeholder_text"))

        if cfg.get("action"):
            act = cfg["action"]
            if act.get("type") in ["custom_web", "web"]:
                idx_b = self.combo_browser_scr.findData(act.get("browser", "default"))
                if idx_b >= 0:
                    self.combo_browser_scr.setCurrentIndex(idx_b)
            if act.get("type") == "custom_app":
                idx_a = self.combo_app_act_scr.findData(act.get("app_action", "open"))
                if idx_a >= 0:
                    self.combo_app_act_scr.setCurrentIndex(idx_a)

        self.screen_macro_panel.setEnabled(True)


    def save_screen_macro(self):
        if not hasattr(self, "current_screen_signal") or not self.current_screen_signal:
            self.show_saved_feedback("Önce dokunmatik ekrandan bir tuş seç")
            return

        cat = self.combo_screen_cat.currentText()
        if "buttons" not in self.config:
            self.config["buttons"] = {}

        page = self.combo_page.currentIndex() + 1
        slot_idx = getattr(self, "current_screen_slot_index", None)

        if cat == tr("no_action"):
            self.config["buttons"].pop(self.current_screen_signal, None)

            # İşlem yok seçilirse Sayfa 3-4 için ekrandaki yazıyı da temizle.
            if page >= 3 and self.serial_thread and self.serial_thread.is_running:
                obj_name = NEXTION_TEXT_OBJ_BY_SLOT.get(page, {}).get(slot_idx)
                if obj_name:
                    nextion_page = f"page{page}"
                    cmd = f'NEXCMD:{nextion_page}.{obj_name}.txt=""' + chr(10)
                    self.serial_thread.send_data(cmd)
        else:
            action_data = self.combo_screen_act.currentData()
            if action_data:
                action_data = action_data.copy()
            action_name = self.combo_screen_act.currentText()
            btn_text = self.input_btn_text.text().strip()

            if action_data and action_data.get("type") in ["custom_web", "custom_app", "custom_hotkey", "type_text"]:
                action_data["custom_arg"] = self.input_screen_custom.text().strip()
            if action_data and action_data.get("type") in ["custom_web", "web"]:
                action_data["browser"] = ["default", "chrome", "edge", "firefox"][self.combo_browser_scr.currentIndex()]
            if action_data and action_data.get("type") == "custom_app":
                action_data["app_action"] = ["open", "close", "force_close"][self.combo_app_act_scr.currentIndex()]

            self.config["buttons"][self.current_screen_signal] = {
                "name": action_name,
                "action": action_data,
                "btn_text": btn_text,
                "details": format_action_details(action_data),
            }

            # Sayfa 3-4 için ekrandaki yazıyı güncelle.
            if page >= 3 and self.serial_thread and self.serial_thread.is_running:
                obj_name = NEXTION_TEXT_OBJ_BY_SLOT.get(page, {}).get(slot_idx)
                if obj_name:
                    nextion_page = f"page{page}"
                    cmd = f'NEXCMD:{nextion_page}.{obj_name}.txt="{btn_text}"\n'
                    self.serial_thread.send_data(cmd)

        save_config(self.config)
        self.refresh_screen_buttons()
        self.show_saved_feedback()


    def setup_log_tab(self):
        layout = QVBoxLayout(self.tab_log)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(14)
        card = QWidget()
        card.setObjectName("GlassCard")
        l = QVBoxLayout(card)
        l.setContentsMargins(22, 22, 22, 22)
        title = QLabel(tr("live_log"))
        title.setObjectName("SectionTitle")
        hint = QLabel(tr("live_log_hint"))
        hint.setObjectName("Muted")
        l.addWidget(title)
        l.addWidget(hint)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        l.addWidget(self.log_area)
        layout.addWidget(card)

    def setup_settings_tab(self):
        layout = QVBoxLayout(self.tab_settings)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_content = QWidget()
        s_layout = QVBoxLayout(scroll_content)
        s_layout.setSpacing(20)

        btn_help = AnimatedButton(tr("help_btn"), accent=lambda: self.current_accent())
        btn_help.setHoverHeights(50, 6)
        btn_help.clicked.connect(self.show_help_popup)
        s_layout.addWidget(btn_help)

        group_profile = QGroupBox("Profil Sistemi")
        l_profile = QVBoxLayout(group_profile)

        lbl_profile_info = QLabel("Farklı kullanım senaryoları için ayrı tuş, ekran ve tekerlek ayarları oluşturabilirsiniz.")
        lbl_profile_info.setWordWrap(True)
        lbl_profile_info.setObjectName("Muted")
        l_profile.addWidget(lbl_profile_info)

        profile_row = QHBoxLayout()
        self.combo_profile = QComboBox()
        self.refresh_profile_combo()
        self.combo_profile.currentIndexChanged.connect(self.change_profile)
        profile_row.addWidget(QLabel("Aktif Profil"))
        profile_row.addWidget(self.combo_profile, 1)
        l_profile.addLayout(profile_row)

        profile_btns = QHBoxLayout()
        self.btn_profile_new = AnimatedButton("➕ Yeni Profil", accent=lambda: self.current_accent())
        self.btn_profile_new.setHoverHeights(42, 5)
        self.btn_profile_new.clicked.connect(self.create_profile)

        self.btn_profile_copy = AnimatedButton("📋 Kopyala", accent=lambda: self.current_accent())
        self.btn_profile_copy.setHoverHeights(42, 5)
        self.btn_profile_copy.clicked.connect(self.copy_profile)

        self.btn_profile_delete = AnimatedButton("🗑️ Sil", accent=lambda: self.current_accent())
        self.btn_profile_delete.setHoverHeights(42, 5)
        self.btn_profile_delete.clicked.connect(self.delete_profile)

        profile_btns.addWidget(self.btn_profile_new)
        profile_btns.addWidget(self.btn_profile_copy)
        profile_btns.addWidget(self.btn_profile_delete)
        l_profile.addLayout(profile_btns)

        s_layout.addWidget(group_profile)

        group_lang = QGroupBox(tr("language"))
        l_lang = QHBoxLayout(group_lang)
        self.combo_lang = QComboBox()
        for code, data in state.TRANSLATIONS.items():
            self.combo_lang.addItem(data.get("lang_name", code), code)
        idx = self.combo_lang.findData(self.config.get("language", "tr"))
        if idx >= 0:
            self.combo_lang.setCurrentIndex(idx)
        self.combo_lang.currentIndexChanged.connect(self.change_language)
        l_lang.addWidget(self.combo_lang)
        l_lang.addStretch()
        s_layout.addWidget(group_lang)

        group_theme = QGroupBox(tr("appearance"))
        l_theme = QHBoxLayout(group_theme)
        l_theme.addWidget(QLabel(tr("accent_color")))
        self.btn_color = AnimatedButton(tr("choose_color"), accent=lambda: self.current_accent())
        self.btn_color.setHoverHeights(42, 5)
        self.btn_color.clicked.connect(self.choose_color)
        l_theme.addWidget(self.btn_color)

        self.btn_reset_color = AnimatedButton(tr("reset_color"), accent=lambda: self.current_accent())
        self.btn_reset_color.setHoverHeights(42, 5)
        self.btn_reset_color.clicked.connect(self.reset_accent_color)
        l_theme.addWidget(self.btn_reset_color)

        l_theme.addStretch()
        s_layout.addWidget(group_theme)

        group_sys = QGroupBox(tr("system"))
        l_sys = QVBoxLayout(group_sys)
        self.chk_startup = AnimatedButton("✅ " + tr("start_win") if self.config.get("start_with_win") else "❌ " + tr("start_win"), accent=lambda: self.current_accent())
        self.chk_startup.setHoverHeights(42, 5)
        self.chk_startup.clicked.connect(self.toggle_startup)
        self.chk_bg = AnimatedButton("✅ " + tr("run_bg") if self.config.get("run_in_bg") else "❌ " + tr("run_bg"), accent=lambda: self.current_accent())
        self.chk_bg.setHoverHeights(42, 5)
        self.chk_bg.clicked.connect(self.toggle_bg)

        self.chk_auto_connect = AnimatedButton("✅ Cihazı otomatik bağla" if self.config.get("auto_connect", True) else "❌ Cihazı otomatik bağla", accent=lambda: self.current_accent())
        self.chk_auto_connect.setHoverHeights(42, 5)
        self.chk_auto_connect.clicked.connect(self.toggle_auto_connect)

        l_sys.addWidget(self.chk_startup)
        l_sys.addWidget(self.chk_bg)
        l_sys.addWidget(self.chk_auto_connect)
        s_layout.addWidget(group_sys)

        # 2.0: Oyun/OBS uyumluluğu ve cihaz yönetimi
        group_compat = QGroupBox("Tuş Gönderimi ve Uyumluluk")
        l_compat = QVBoxLayout(group_compat)
        lbl_compat = QLabel(
            "Bazı oyunlar (ör. hile korumalı oyunlar) yazılımla gönderilen tuşları yok sayar. "
            "2.0 firmware yüklü NexDeck, tuşları gerçek USB klavye gibi gönderebilir. "
            "Yönetici olarak çalışan programlara tuş göndermek için NexStudio da yönetici olarak çalışmalıdır."
        )
        lbl_compat.setWordWrap(True)
        lbl_compat.setObjectName("Muted")
        l_compat.addWidget(lbl_compat)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Tuş gönderim yöntemi"))
        self.combo_key_mode = QComboBox()
        self.combo_key_mode.addItem("Otomatik (cihaz destekliyorsa USB klavye)", "auto")
        self.combo_key_mode.addItem("Sadece yazılım (SendInput)", "software")
        idx = self.combo_key_mode.findData(self.config.get("key_send_mode", "auto"))
        self.combo_key_mode.setCurrentIndex(max(0, idx))
        self.combo_key_mode.currentIndexChanged.connect(self.change_key_send_mode)
        mode_row.addWidget(self.combo_key_mode, 1)
        l_compat.addLayout(mode_row)

        compat_btns = QVBoxLayout()
        self.btn_run_admin = AnimatedButton(
            "🛡️ Yönetici olarak çalışıyor" if is_process_elevated() else "🛡️ Yönetici olarak yeniden başlat",
            accent=lambda: self.current_accent())
        self.btn_run_admin.setHoverHeights(42, 5)
        self.btn_run_admin.setEnabled(not is_process_elevated())
        self.btn_run_admin.clicked.connect(self.restart_as_admin)
        btn_rename_deck = AnimatedButton("✏️ Bağlı cihazı adlandır", accent=lambda: self.current_accent())
        btn_rename_deck.setHoverHeights(42, 5)
        btn_rename_deck.clicked.connect(self.rename_connected_deck)
        btn_error_log = AnimatedButton("🧾 Hata günlüğünü aç", accent=lambda: self.current_accent())
        btn_error_log.setHoverHeights(42, 5)
        btn_error_log.clicked.connect(self.open_error_log)
        btn_modern = AnimatedButton("✨ Yeni görünüme geç", accent=lambda: self.current_accent())
        btn_modern.setHoverHeights(42, 5)
        btn_modern.clicked.connect(lambda: self.switch_ui_mode("modern"))
        compat_btns.addWidget(btn_modern)
        compat_btns.addWidget(self.btn_run_admin)
        compat_btns.addWidget(btn_rename_deck)
        compat_btns.addWidget(btn_error_log)
        l_compat.addLayout(compat_btns)
        s_layout.addWidget(group_compat)

        group_log_settings = QGroupBox("Sistem Günlüğü")
        l_log_settings = QVBoxLayout(group_log_settings)
        lbl_log_settings = QLabel("Web girişleri, hatalı PIN denemeleri, yetkisiz erişimler ve cihaz sinyalleri burada takip edilir. Normal kullanıcılar için sol menüde gizlenebilir.")
        lbl_log_settings.setWordWrap(True)
        lbl_log_settings.setObjectName("Muted")
        l_log_settings.addWidget(lbl_log_settings)

        self.btn_log_visibility = AnimatedButton(("✅ " if self.config.get("show_system_log_menu", False) else "❌ ") + "Sistem Günlüğü sol menüde görünsün", accent=lambda: self.current_accent())
        self.btn_log_visibility.setHoverHeights(42, 5)
        self.btn_log_visibility.clicked.connect(self.toggle_system_log_menu)
        l_log_settings.addWidget(self.btn_log_visibility)

        btn_open_log = AnimatedButton("📜 Sistem Günlüğünü Aç", accent=lambda: self.current_accent())
        btn_open_log.setHoverHeights(42, 5)
        btn_open_log.clicked.connect(self.open_system_log_from_settings)
        l_log_settings.addWidget(btn_open_log)

        log_btn_row = QHBoxLayout()
        self.btn_clear_log = AnimatedButton("🧹 Sistem Günlüğünü Temizle", accent=lambda: self.current_accent())
        self.btn_clear_log.setHoverHeights(42, 5)
        self.btn_clear_log.clicked.connect(self.clear_system_log)
        self.btn_export_log = AnimatedButton("💾 Günlüğü TXT Dışa Aktar", accent=lambda: self.current_accent())
        self.btn_export_log.setHoverHeights(42, 5)
        self.btn_export_log.clicked.connect(self.export_system_log)
        log_btn_row.addWidget(self.btn_clear_log)
        log_btn_row.addWidget(self.btn_export_log)
        l_log_settings.addLayout(log_btn_row)

        self.btn_history_toggle = AnimatedButton("📜 Web Giriş Geçmişini Göster", accent=lambda: self.current_accent())
        self.btn_history_toggle.setHoverHeights(42, 5)
        self.btn_history_toggle.clicked.connect(self.toggle_web_history_panel)
        l_log_settings.addWidget(self.btn_history_toggle)
        self.list_web_history = QListWidget()
        self.list_web_history.setMinimumHeight(140)
        self.list_web_history.setVisible(False)
        l_log_settings.addWidget(self.list_web_history)
        s_layout.addWidget(group_log_settings)

        group_web_sec = QGroupBox("Web Güvenliği ve Tanınan Cihazlar")
        l_web_sec = QVBoxLayout(group_web_sec)
        lbl_web_sec = QLabel("PIN, oturum, otomatik web başlatma ve tanınan cihaz ayarlarını buradan yönetebilirsiniz.")
        lbl_web_sec.setWordWrap(True)
        lbl_web_sec.setObjectName("Muted")
        l_web_sec.addWidget(lbl_web_sec)

        self.btn_web_auto_start = AnimatedButton(("✅ " if self.config.get("web_auto_start", False) else "❌ ") + "Uygulama açılınca Web Kontrolü otomatik başlasın", accent=lambda: self.current_accent())
        self.btn_web_auto_start.setHoverHeights(42, 5)
        self.btn_web_auto_start.clicked.connect(self.toggle_web_auto_start)
        l_web_sec.addWidget(self.btn_web_auto_start)

        self.btn_web_private_log = AnimatedButton(("✅ " if self.config.get("web_private_log", False) else "❌ ") + "Günlükte IP adreslerini gizle", accent=lambda: self.current_accent())
        self.btn_web_private_log.setHoverHeights(42, 5)
        self.btn_web_private_log.clicked.connect(self.toggle_web_private_log)
        l_web_sec.addWidget(self.btn_web_private_log)

        self.btn_web_known_only = AnimatedButton(("✅ " if self.config.get("web_known_only", False) else "❌ ") + "Sadece tanınan cihazlar Web Kontrolü kullanabilsin", accent=lambda: self.current_accent())
        self.btn_web_known_only.setHoverHeights(42, 5)
        self.btn_web_known_only.clicked.connect(self.toggle_web_known_only)
        l_web_sec.addWidget(self.btn_web_known_only)

        lbl_web_quick_hint = QLabel("PIN yenileme ve web oturumlarını sıfırlama işlemleri artık Web Kontrolü sekmesindeki hızlı güvenlik kartından yapılır.")
        lbl_web_quick_hint.setWordWrap(True)
        lbl_web_quick_hint.setObjectName("Muted")
        l_web_sec.addWidget(lbl_web_quick_hint)

        self.lbl_settings_last_device = QLabel("Son bağlantı: -")
        self.lbl_settings_last_device.setWordWrap(True)
        self.lbl_settings_last_device.setStyleSheet("color: #C7D2FE; font-weight: 800; background: rgba(59,130,246,.08); border: 1px solid rgba(96,165,250,.16); border-radius: 10px; padding: 8px 10px;")
        l_web_sec.addWidget(self.lbl_settings_last_device)

        device_row = QHBoxLayout()
        self.combo_known_devices = QComboBox()
        device_row.addWidget(QLabel("Tanınan cihaz:"))
        device_row.addWidget(self.combo_known_devices, 1)
        l_web_sec.addLayout(device_row)

        device_btn_row = QHBoxLayout()
        self.btn_rename_device = AnimatedButton("✏️ Cihazı Adlandır", accent=lambda: self.current_accent())
        self.btn_rename_device.setHoverHeights(42, 5)
        self.btn_rename_device.clicked.connect(self.rename_known_device)
        self.btn_forget_device = AnimatedButton("🗑️ Cihazı Unut", accent=lambda: self.current_accent())
        self.btn_forget_device.setHoverHeights(42, 5)
        self.btn_forget_device.clicked.connect(self.forget_known_device)
        device_btn_row.addWidget(self.btn_rename_device)
        device_btn_row.addWidget(self.btn_forget_device)
        l_web_sec.addLayout(device_btn_row)
        s_layout.addWidget(group_web_sec)
        self.refresh_web_security_panel()

        group_account = QGroupBox(tr("tab_account"))
        l_acc = QVBoxLayout(group_account)
        badge = QLabel(tr("dev_stage"))
        badge.setObjectName("StatusPill")
        l_acc.addWidget(badge)
        lbl_desc = QLabel(tr("account_dev_desc"))
        lbl_desc.setWordWrap(True)
        lbl_desc.setObjectName("Muted")
        l_acc.addWidget(lbl_desc)
        self.inp_email = QLineEdit()
        self.inp_email.setPlaceholderText(tr("acc_email"))
        self.inp_email.setEnabled(False)
        l_acc.addWidget(self.inp_email)
        self.inp_pass = QLineEdit()
        self.inp_pass.setPlaceholderText(tr("acc_pass"))
        self.inp_pass.setEchoMode(QLineEdit.Password)
        self.inp_pass.setEnabled(False)
        l_acc.addWidget(self.inp_pass)
        btn_layout = QHBoxLayout()
        btn_login = AnimatedButton(tr("acc_login"), accent=lambda: self.current_accent())
        btn_login.setHoverHeights(42, 5)
        btn_login.setEnabled(False)
        btn_register = AnimatedButton(tr("acc_register"), accent=lambda: self.current_accent())
        btn_register.setHoverHeights(42, 5)
        btn_register.setEnabled(False)
        btn_layout.addWidget(btn_login)
        btn_layout.addWidget(btn_register)
        l_acc.addLayout(btn_layout)
        s_layout.addWidget(group_account)

        group_plugins = QGroupBox(tr("plugin_manage"))
        l_plugins = QHBoxLayout(group_plugins)
        btn_open_plugins = AnimatedButton(tr("open_plugins"), accent=lambda: self.current_accent())
        btn_open_plugins.setHoverHeights(42, 5)
        btn_open_plugins.clicked.connect(lambda: os.startfile(PLUGINS_DIR))
        btn_open_locales = AnimatedButton(tr("open_locales"), accent=lambda: self.current_accent())
        btn_open_locales.setHoverHeights(42, 5)
        btn_open_locales.clicked.connect(lambda: os.startfile(LOCALES_DIR))
        l_plugins.addWidget(btn_open_plugins)
        l_plugins.addWidget(btn_open_locales)
        s_layout.addWidget(group_plugins)

        group_reset = QGroupBox(tr("danger_zone"))
        l_reset = QVBoxLayout(group_reset)
        btn_restart = AnimatedButton(tr("restart_app"), accent=lambda: self.current_accent())
        btn_restart.setHoverHeights(42, 5)
        btn_restart.clicked.connect(self.restart_app)
        l_reset.addWidget(btn_restart)
        btn_reset = AnimatedButton(tr("factory_reset"), accent=lambda: self.current_accent())
        btn_reset.setHoverHeights(42, 5)
        btn_reset.clicked.connect(self.factory_reset)
        l_reset.addWidget(btn_reset)
        s_layout.addWidget(group_reset)

        s_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

    def setup_web_tab(self):
        layout = QVBoxLayout(self.tab_web)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        info = self.build_web_info_cards()

        top_row = QHBoxLayout()
        top_row.setSpacing(18)

        card_intro = HoverScaleFrame(grow_by=8)
        card_intro.setObjectName("GlassCard")
        card_intro.setHoverHeights(190, 10)
        ci_l = QVBoxLayout(card_intro)
        ci_l.setContentsMargins(20, 20, 20, 20)
        ci_l.setSpacing(10)
        lbl_intro_title = QLabel(tr("web_control_title"))
        lbl_intro_title.setObjectName("SectionTitle")
        ci_l.addWidget(lbl_intro_title)
        lbl_stage = QLabel(tr("dev_stage"))
        lbl_stage.setObjectName("StatusPill")
        ci_l.addWidget(lbl_stage)
        lbl_intro_desc = QLabel(info["overview_desc"])
        lbl_intro_desc.setWordWrap(True)
        lbl_intro_desc.setObjectName("Muted")
        ci_l.addWidget(lbl_intro_desc)
        ci_l.addStretch()
        top_row.addWidget(card_intro, 1)

        card_notes = HoverScaleFrame(grow_by=8)
        card_notes.setObjectName("GlassCard")
        card_notes.setHoverHeights(190, 10)
        cn_l = QVBoxLayout(card_notes)
        cn_l.setContentsMargins(20, 20, 20, 20)
        cn_l.setSpacing(10)
        lbl_notes_title = QLabel(info["notes_title"])
        lbl_notes_title.setObjectName("SectionTitle")
        cn_l.addWidget(lbl_notes_title)
        lbl_notes_desc = QLabel(info["notes_desc"])
        lbl_notes_desc.setWordWrap(True)
        lbl_notes_desc.setObjectName("Muted")
        cn_l.addWidget(lbl_notes_desc)
        cn_l.addStretch()
        top_row.addWidget(card_notes, 1)

        layout.addLayout(top_row)

        middle_row = QVBoxLayout()
        middle_row.setSpacing(18)

        group_mobile = HoverScaleFrame(grow_by=8)
        group_mobile.setObjectName("GlassCard")
        group_mobile.setHoverHeights(360, 10)
        l_mobile = QVBoxLayout(group_mobile)
        l_mobile.setContentsMargins(20, 20, 20, 20)
        l_mobile.setSpacing(12)
        lbl_mobile_title = QLabel(tr("tab_web"))
        lbl_mobile_title.setObjectName("SectionTitle")
        l_mobile.addWidget(lbl_mobile_title)
        mobile_layout = QGridLayout()
        mobile_layout.setContentsMargins(0, 0, 0, 0)
        mobile_layout.setHorizontalSpacing(8)
        mobile_layout.setVerticalSpacing(8)

        self.btn_mobile = AnimatedButton("📱 Başlat", accent=lambda: self.current_accent())
        self.btn_mobile.setHoverHeights(40, 4)
        self.btn_mobile.setMinimumWidth(118)
        self.btn_mobile.clicked.connect(self.toggle_mobile_server)
        mobile_layout.addWidget(self.btn_mobile, 0, 0)

        self.btn_web_sensitive_toggle = AnimatedButton("🔐 Gizli Bilgiler", accent=lambda: self.current_accent())
        self.btn_web_sensitive_toggle.setHoverHeights(40, 4)
        self.btn_web_sensitive_toggle.setMinimumWidth(150)
        self.btn_web_sensitive_toggle.clicked.connect(self.show_web_sensitive_dialog)
        mobile_layout.addWidget(self.btn_web_sensitive_toggle, 0, 1)

        self.btn_copy_web_url = AnimatedButton("🔗 Kopyala", accent=lambda: self.current_accent())
        self.btn_copy_web_url.setHoverHeights(40, 4)
        self.btn_copy_web_url.setMinimumWidth(108)
        self.btn_copy_web_url.clicked.connect(self.copy_web_url)
        self.btn_copy_web_url.setVisible(False)
        mobile_layout.addWidget(self.btn_copy_web_url, 0, 2)

        self.btn_big_qr = AnimatedButton("🔍 QR Büyüt", accent=lambda: self.current_accent())
        self.btn_big_qr.setHoverHeights(40, 4)
        self.btn_big_qr.setMinimumWidth(118)
        self.btn_big_qr.clicked.connect(self.show_qr_large)
        self.btn_big_qr.setVisible(False)
        mobile_layout.addWidget(self.btn_big_qr, 0, 3)

        mobile_layout.setColumnStretch(4, 1)
        l_mobile.addLayout(mobile_layout)

        self.lbl_web_status_public = QLabel("Web Kontrolü: Kapalı")
        self.lbl_web_status_public.setWordWrap(True)
        self.lbl_web_status_public.setStyleSheet("color: #CBD5E1; font-weight: 800; font-size: 12px; background: rgba(15,23,42,.45); border: 1px solid rgba(148,163,184,.16); border-radius: 12px; padding: 8px 10px;")
        l_mobile.addWidget(self.lbl_web_status_public)

        self.lbl_last_device = QLabel("Son bağlantı: -")
        self.lbl_last_device.setWordWrap(True)
        self.lbl_last_device.setStyleSheet("color: #C7D2FE; font-weight: 800; font-size: 12px; background: rgba(59,130,246,.08); border: 1px solid rgba(96,165,250,.16); border-radius: 12px; padding: 8px 10px;")
        l_mobile.addWidget(self.lbl_last_device)

        # Son cihazı adlandırma yönetimi Ayarlar > Tanınan Cihazlar bölümünde tutulur.
        self.btn_rename_last_device = AnimatedButton("✏️ Son Cihazı Adlandır", accent=lambda: self.current_accent())
        self.btn_rename_last_device.setHoverHeights(40, 4)
        self.btn_rename_last_device.clicked.connect(self.rename_last_web_device)
        self.btn_rename_last_device.setVisible(False)

        self.web_sensitive_panel = QFrame()
        self.web_sensitive_panel.setObjectName("GlassCard")
        self.web_sensitive_panel.setStyleSheet("QFrame#GlassCard { background: rgba(2,6,23,.22); border: 1px solid rgba(148,163,184,.14); border-radius: 16px; }")
        self.web_sensitive_panel.setVisible(False)
        sensitive_layout = QVBoxLayout(self.web_sensitive_panel)
        sensitive_layout.setContentsMargins(12, 12, 12, 12)
        sensitive_layout.setSpacing(10)

        self.lbl_mobile_ip = QLabel("")
        self.lbl_mobile_ip.setAlignment(Qt.AlignCenter)
        self.lbl_mobile_ip.setStyleSheet("color: #10B981; font-weight: 950; font-size: 13px; background: rgba(16,185,129,.10); border: 1px solid rgba(16,185,129,.30); border-radius: 12px; padding: 8px 10px;")
        sensitive_layout.addWidget(self.lbl_mobile_ip)

        self.lbl_web_status = QLabel("Web Kontrolü: Kapalı")
        self.lbl_web_status.setWordWrap(True)
        self.lbl_web_status.setStyleSheet("color: #CBD5E1; font-weight: 800; font-size: 12px; background: rgba(15,23,42,.45); border: 1px solid rgba(148,163,184,.16); border-radius: 12px; padding: 8px 10px;")
        sensitive_layout.addWidget(self.lbl_web_status)

        security_tools_row = QGridLayout()
        security_tools_row.setHorizontalSpacing(8)
        security_tools_row.setVerticalSpacing(8)

        self.btn_toggle_url = AnimatedButton("👁 URL", accent=lambda: self.current_accent())
        self.btn_toggle_url.setHoverHeights(40, 4)
        self.btn_toggle_url.clicked.connect(self.toggle_web_url)
        self.btn_toggle_url.setVisible(False)
        security_tools_row.addWidget(self.btn_toggle_url, 0, 0)

        self.btn_qr = AnimatedButton("👁 QR", accent=lambda: self.current_accent())
        self.btn_qr.setHoverHeights(40, 4)
        self.btn_qr.clicked.connect(self.toggle_qr)
        self.btn_qr.setVisible(False)
        security_tools_row.addWidget(self.btn_qr, 0, 1)

        self.btn_web_page_regen_pin = AnimatedButton("🔐 PIN Yenile", accent=lambda: self.current_accent())
        self.btn_web_page_regen_pin.setHoverHeights(40, 4)
        self.btn_web_page_regen_pin.clicked.connect(self.regenerate_web_pin)
        security_tools_row.addWidget(self.btn_web_page_regen_pin, 1, 0)

        self.btn_web_page_reset_sessions = AnimatedButton("🔁 QR / Link Yenile", accent=lambda: self.current_accent())
        self.btn_web_page_reset_sessions.setHoverHeights(40, 4)
        self.btn_web_page_reset_sessions.clicked.connect(self.reset_web_sessions)
        security_tools_row.addWidget(self.btn_web_page_reset_sessions, 1, 1)
        sensitive_layout.addLayout(security_tools_row)

        self.lbl_web_url = QLabel("")
        self.lbl_web_url.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_web_url.setWordWrap(True)
        self.lbl_web_url.setStyleSheet("color: #93C5FD; font-weight: 800; font-size: 12px; background: rgba(15,23,42,.45); border: 1px solid rgba(148,163,184,.16); border-radius: 12px; padding: 7px 10px;")
        self.lbl_web_url.setVisible(False)
        sensitive_layout.addWidget(self.lbl_web_url)

        qr_wrap = QHBoxLayout()
        self.lbl_qr_image = QLabel()
        self.lbl_qr_image.setFixedSize(176, 176)
        self.lbl_qr_image.setScaledContents(True)
        self.lbl_qr_image.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.lbl_qr_image.setVisible(False)
        qr_wrap.addWidget(self.lbl_qr_image, alignment=Qt.AlignLeft)
        qr_wrap.addStretch()
        sensitive_layout.addLayout(qr_wrap)
        l_mobile.addWidget(self.web_sensitive_panel)
        l_mobile.addStretch()
        middle_row.addWidget(group_mobile)

        roadmap_card = HoverScaleFrame(grow_by=8)
        roadmap_card.setObjectName("GlassCard")
        roadmap_card.setHoverHeights(190, 8)
        rr_l = QVBoxLayout(roadmap_card)
        rr_l.setContentsMargins(20, 20, 20, 20)
        rr_l.setSpacing(10)
        lbl_roadmap = QLabel(info["roadmap_title"])
        lbl_roadmap.setObjectName("SectionTitle")
        rr_l.addWidget(lbl_roadmap)
        for item in info["roadmap_items"]:
            lbl_item = QLabel(f"• {item}")
            lbl_item.setWordWrap(True)
            lbl_item.setObjectName("Muted")
            rr_l.addWidget(lbl_item)
        rr_l.addStretch()
        middle_row.addWidget(roadmap_card)

        layout.addLayout(middle_row)
        layout.addStretch()

    def show_help_popup(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("help_btn"))
        dialog.setMinimumWidth(500)
        dialog.setStyleSheet(get_stylesheet(self.config.get("accent_color", self.config.get("accent_color", "#3B82F6"))))
        l = QVBoxLayout(dialog)
        lbl_title = QLabel(tr("help_title"))
        lbl_title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        lbl_title.setStyleSheet(f"color: {self.config.get('accent_color', self.config.get("accent_color", "#3B82F6"))};")
        l.addWidget(lbl_title)
        info_text = tr("help_html")
        lbl_info = QLabel(info_text)
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("font-size: 14px; line-height: 1.5;")
        l.addWidget(lbl_info)
        l.addStretch()
        btn_yt = QPushButton(tr("help_video"))
        btn_yt.setStyleSheet("background-color: #EF4444; color: white; font-size: 16px; padding: 15px; border-radius: 8px; font-weight: bold;")
        btn_yt.clicked.connect(lambda: webbrowser.open(NEXHUB_YOUTUBE_CHANNEL))
        l.addWidget(btn_yt)
        dialog.exec_()

    def refresh_web_control_status(self):
        try:
            is_on = bool(self.mobile_thread and self.mobile_thread.is_running)
            port = self.current_mobile_port or self.config.get("last_mobile_port", DEFAULT_MOBILE_PORT)
            pin = self.config.get("mobile_pin", "") or "-"
            known_count = len(self.config.get("known_web_devices", {}) or {})
            history = self.config.get("web_access_history", []) if isinstance(self.config.get("web_access_history", []), list) else []
            last = history[0] if history else {}
            last_name = last.get("device_name", "-")
            last_time = last.get("time", "-")
            last_type = last.get("device_type", "")
            last_browser = last.get("browser", "")
            last_ip = last.get("ip_display", last.get("ip", "-"))
            self.last_web_device_id = last.get("device_id", "") if isinstance(last, dict) else ""
            status = "Açık" if is_on else "Kapalı"
            url = getattr(self, "current_web_url", "") or "-"
            public_text = f"Web Kontrolü: {status}  •  Port: {port}  •  Tanınan cihaz: {known_count}\nGüvenlik: PIN + özel bağlantı aktif  •  Gizli bilgiler ayrı panelde"
            detail_text = f"Web Kontrolü: {status}  •  Port: {port}  •  PIN: {pin}\nSon giriş: {last_name} ({last_time})  •  Tanınan cihaz: {known_count}\nBağlantı: {url}"
            last_text = f"Son bağlantı: {last_name}"
            if last_time and last_time != "-":
                last_text += f" • {last_time}"
            if last_type or last_browser:
                last_text += f"\nCihaz: {last_type or '-'} / {last_browser or '-'}  •  IP: {last_ip}"
            if hasattr(self, "lbl_web_status_public"):
                self.lbl_web_status_public.setText(public_text)
            if hasattr(self, "lbl_web_status"):
                self.lbl_web_status.setText(detail_text)
            if hasattr(self, "lbl_last_device"):
                self.lbl_last_device.setText(last_text)
            if hasattr(self, "btn_rename_last_device"):
                self.btn_rename_last_device.setVisible(False)
            self.update_web_sensitive_widgets()
        except Exception:
            pass

    def toggle_mobile_server(self):
        if self.mobile_thread and self.mobile_thread.is_running:
            thread = self.mobile_thread
            try:
                thread.stop()
                thread.wait(1500)
            except Exception:
                pass
            self.mobile_thread = None
            self.current_mobile_port = None

            self.btn_mobile.setText("📱 Başlat")
            self.lbl_mobile_ip.setText("")
            if hasattr(self, "lbl_web_url"):
                self.lbl_web_url.setText("")
                self.lbl_web_url.setVisible(False)
            if hasattr(self, "btn_toggle_url"):
                self.btn_toggle_url.setText("👁 URL")
                self.btn_toggle_url.setVisible(False)
            if hasattr(self, "btn_copy_web_url"):
                self.btn_copy_web_url.setVisible(False)
            self.btn_qr.setText("👁 QR")
            self.btn_qr.setVisible(False)
            self.lbl_qr_image.setVisible(False)
            self.refresh_web_control_status()
            self.update_web_sensitive_widgets()
        else:
            alphabet = string.ascii_uppercase + string.digits
            new_pin = ''.join(secrets.choice(alphabet) for _ in range(6))
            self.config["mobile_pin"] = new_pin
            token = secrets.token_urlsafe(8)
            self.config["web_token"] = token
            port = find_available_port()

            if port is None:

                QMessageBox.warning(self, "Web Kontrolü", "Boş web portu bulunamadı. Açık NexDeck.exe süreçlerini kapatıp tekrar deneyin.")

                return

            

            self.config["last_mobile_port"] = port

            if hasattr(self, "log_area"):
                if port != DEFAULT_MOBILE_PORT:
                    ui_log(f"🌐 Varsayılan port dolu olduğu için Web Kontrolü {port} portundan başlatılacak.")
                else:
                    ui_log(f"🌐 Web Kontrolü için port ayrıldı: {port}")

            save_config(self.config)

            

            self.refresh_web_security_panel()
            self.mobile_thread = MobileServerThread(port)
            self.mobile_thread.server_started.connect(self.on_mobile_server_started)
            self.mobile_thread.server_failed.connect(self.on_mobile_server_failed)

            self.current_mobile_port = port

            self.mobile_thread.start()
            self.btn_mobile.setText("⏹ Durdur")

            ip = get_local_ip()

            url = f"http://{ip}:{port}/{token}"
            self.current_web_url = url
            self.lbl_mobile_ip.setText(f"PIN: {new_pin}")
            if hasattr(self, "lbl_web_url"):
                self.lbl_web_url.setText(url)
                self.lbl_web_url.setVisible(False)
            if hasattr(self, "btn_toggle_url"):
                self.btn_toggle_url.setText("👁 URL")
                self.btn_toggle_url.setVisible(True)
            if hasattr(self, "btn_copy_web_url"):
                self.btn_copy_web_url.setVisible(True)
            
            if HAS_QR:
                qr = qrcode.QRCode(version=1, box_size=4, border=4)
                qr.add_data(url)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                img = img.convert("RGBA")
                data = img.tobytes("raw", "RGBA")
                qim = QImage(data, img.size[0], img.size[1], QImage.Format_RGBA8888)
                self.lbl_qr_image.setPixmap(QPixmap.fromImage(qim))
                self.btn_qr.setVisible(True)
            else: self.lbl_mobile_ip.setText(tr("qr_missing").format(url))
            self.refresh_web_control_status()
            self.update_web_sensitive_widgets()

    def on_mobile_server_started(self, port):
        try:
            if hasattr(self, "log_area"):
                ui_log(f"🌐 Web Kontrolü başlatıldı: Port {port}")
            self.refresh_web_control_status()
        except Exception:
            pass

    def on_mobile_server_failed(self, error_text):
        try:
            self.mobile_thread = None
            self.current_mobile_port = None
            if hasattr(self, "btn_mobile"):
                self.btn_mobile.setText("📱 Başlat")
            if hasattr(self, "lbl_mobile_ip"):
                self.lbl_mobile_ip.setText("Web Hatası")
            if hasattr(self, "log_area"):
                ui_log(f"⚠️ Web Kontrolü Hatası: {error_text}")
            self.refresh_web_control_status()
            QMessageBox.warning(
                self,
                "Web Kontrolü",
                "Web sunucusu başlatılamadı.\n\n"
                f"Hata:\n{error_text}\n\n"
                "Olası sebepler:\n"
                "- Aynı portu kullanan eski NexStudio süreci açık olabilir.\n"
                "- Windows Güvenlik Duvarı exe bağlantısını engelliyor olabilir.\n"
                "- PyInstaller paketine gerekli modüller eklenmemiş olabilir."
            )
        except Exception:
            pass

    def copy_web_url(self):
        url = getattr(self, "current_web_url", "")
        if url:
            QApplication.clipboard().setText(url)
            self.show_saved_feedback("Web bağlantısı kopyalandı")

    def update_web_sensitive_widgets(self):
        try:
            is_on = bool(self.mobile_thread and self.mobile_thread.is_running)
            sensitive = False
            if hasattr(self, "web_sensitive_panel"):
                self.web_sensitive_panel.setVisible(False)
            if hasattr(self, "btn_web_sensitive_toggle"):
                self.btn_web_sensitive_toggle.setText("🔐 Gizli Bilgiler")
            if hasattr(self, "btn_copy_web_url"):
                self.btn_copy_web_url.setVisible(is_on)
            if hasattr(self, "btn_big_qr"):
                self.btn_big_qr.setVisible(is_on and HAS_QR)
            if hasattr(self, "btn_toggle_url"):
                self.btn_toggle_url.setVisible(is_on)
            if hasattr(self, "btn_qr"):
                self.btn_qr.setVisible(is_on and HAS_QR)
            if not sensitive:
                if hasattr(self, "lbl_web_url"):
                    self.lbl_web_url.setVisible(False)
                if hasattr(self, "lbl_qr_image"):
                    self.lbl_qr_image.setVisible(False)
                if hasattr(self, "btn_toggle_url"):
                    self.btn_toggle_url.setText("👁 URL")
                if hasattr(self, "btn_qr"):
                    self.btn_qr.setText("👁 QR")
        except Exception:
            pass

    def toggle_web_sensitive_panel(self):
        self.show_web_sensitive_dialog()

    def toggle_web_url(self):
        if not hasattr(self, "lbl_web_url"):
            return
        self.web_sensitive_visible = True
        visible = not self.lbl_web_url.isVisible()
        self.lbl_web_url.setVisible(visible)
        if hasattr(self, "btn_toggle_url"):
            self.btn_toggle_url.setText("🙈 URL" if visible else "👁 URL")
        self.update_web_sensitive_widgets()

    def toggle_qr(self):
        self.web_sensitive_visible = True
        visible = not self.lbl_qr_image.isVisible()
        self.lbl_qr_image.setVisible(visible)
        self.btn_qr.setText("🙈 QR" if visible else "👁 QR")
        self.update_web_sensitive_widgets()

    def show_web_sensitive_dialog(self):
        try:
            if not (self.mobile_thread and self.mobile_thread.is_running):
                self.show_saved_feedback("Web Kontrolü kapalı")
                return

            dialog = QDialog(self)
            dialog.setWindowTitle("Gizli Web Bilgileri")
            dialog.setMinimumSize(520, 430)
            dialog.setStyleSheet(get_stylesheet(self.config.get("accent_color", "#3B82F6")))
            layout = QVBoxLayout(dialog)
            layout.setSpacing(12)

            title = QLabel("Gizli Web Bilgileri")
            title.setObjectName("SectionTitle")
            layout.addWidget(title)

            hint = QLabel("PIN ve bağlantı bilgileri yalnızca güvenilir kişilerle paylaşılmalıdır. QR kodu ayrı büyütme penceresinde gösterilir.")
            hint.setWordWrap(True)
            hint.setObjectName("Muted")
            layout.addWidget(hint)

            pin_lbl = QLabel(f"PIN: {self.config.get('mobile_pin', '-')}")
            pin_lbl.setAlignment(Qt.AlignCenter)
            pin_lbl.setStyleSheet("font-size: 24px; font-weight: 950; letter-spacing: 4px; color: #10B981; background: rgba(16,185,129,.10); border: 1px solid rgba(16,185,129,.30); border-radius: 14px; padding: 12px;")
            layout.addWidget(pin_lbl)

            url_lbl = QLabel(getattr(self, "current_web_url", "-"))
            url_lbl.setWordWrap(True)
            url_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            url_lbl.setStyleSheet("color: #93C5FD; font-weight: 800; background: rgba(15,23,42,.45); border: 1px solid rgba(148,163,184,.16); border-radius: 12px; padding: 10px;")
            layout.addWidget(url_lbl)

            btn_grid = QGridLayout()
            btn_grid.setHorizontalSpacing(8)
            btn_grid.setVerticalSpacing(8)

            btn_copy = AnimatedButton("🔗 Bağlantıyı Kopyala", accent=lambda: self.current_accent())
            btn_copy.setHoverHeights(42, 5)
            btn_copy.clicked.connect(lambda: (self.copy_web_url(), dialog.raise_()))
            btn_grid.addWidget(btn_copy, 0, 0)

            btn_pin = AnimatedButton("🔐 PIN Yenile", accent=lambda: self.current_accent())
            btn_pin.setHoverHeights(42, 5)
            btn_pin.clicked.connect(lambda: (self.regenerate_web_pin(), pin_lbl.setText(f"PIN: {self.config.get('mobile_pin', '-')}")))
            btn_grid.addWidget(btn_pin, 0, 1)

            btn_reset = AnimatedButton("🔁 QR / Link Yenile", accent=lambda: self.current_accent())
            btn_reset.setHoverHeights(42, 5)
            def _reset_and_update():
                self.reset_web_sessions()
                pin_lbl.setText(f"PIN: {self.config.get('mobile_pin', '-')}")
                url_lbl.setText(getattr(self, "current_web_url", "-"))
            btn_reset.clicked.connect(_reset_and_update)
            btn_grid.addWidget(btn_reset, 1, 0)

            layout.addLayout(btn_grid)

            qr_hint = QLabel("QR kodu ana Web Kontrolü ekranındaki 'QR Büyüt' butonundan ayrı pencerede açılır. Bu panelde QR bilerek gösterilmez.")
            qr_hint.setWordWrap(True)
            qr_hint.setObjectName("Muted")
            layout.addWidget(qr_hint)

            layout.addStretch()
            dialog.exec_()
        except Exception as e:
            QMessageBox.warning(self, "Gizli Web Bilgileri", f"Panel açılamadı:\n{e}")

    def show_qr_large(self):
        try:
            if not hasattr(self, "lbl_qr_image") or self.lbl_qr_image.pixmap() is None or self.lbl_qr_image.pixmap().isNull():
                self.show_saved_feedback("QR henüz oluşturulmadı")
                return
            dialog = QDialog(self)
            dialog.setWindowTitle("NexStudio QR Kodu")
            dialog.setMinimumSize(460, 560)
            dialog.setStyleSheet(get_stylesheet(self.config.get("accent_color", "#3B82F6")))
            layout = QVBoxLayout(dialog)
            title = QLabel("Web Kontrolü QR Kodu")
            title.setObjectName("SectionTitle")
            layout.addWidget(title)
            hint = QLabel("Telefon veya tablet ile bu QR kodu okutabilirsin. PIN kodu aşağıdadır.")
            hint.setWordWrap(True)
            hint.setObjectName("Muted")
            layout.addWidget(hint)
            qr_lbl = QLabel()
            qr_lbl.setAlignment(Qt.AlignCenter)
            qr_lbl.setPixmap(self.lbl_qr_image.pixmap().scaled(360, 360, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            layout.addWidget(qr_lbl, alignment=Qt.AlignCenter)
            pin_lbl = QLabel(f"PIN: {self.config.get('mobile_pin', '-')}")
            pin_lbl.setAlignment(Qt.AlignCenter)
            pin_lbl.setStyleSheet("font-size: 24px; font-weight: 950; letter-spacing: 4px; color: #10B981;")
            layout.addWidget(pin_lbl)
            dialog.exec_()
        except Exception as e:
            QMessageBox.warning(self, "QR Kodu", f"QR büyütülemedi:\n{e}")

    def rename_last_web_device(self):
        try:
            device_id = getattr(self, "last_web_device_id", "")
            if not device_id:
                self.show_saved_feedback("Son cihaz bulunamadı")
                return
            known = self.config.get("known_web_devices", {})
            if not isinstance(known, dict) or device_id not in known:
                self.show_saved_feedback("Cihaz henüz tanınan listede değil")
                return
            current_name = known.get(device_id, {}).get("name", "")
            new_name, ok = QInputDialog.getText(self, "Cihazı Adlandır", "Bu cihaz için görünen ad:", text=current_name)
            if ok and new_name.strip():
                known[device_id]["name"] = new_name.strip()
                self.config["known_web_devices"] = known
                save_config(self.config)
                self.refresh_web_security_panel()
                self.refresh_web_control_status()
                self.show_saved_feedback("Cihaz adı kaydedildi")
        except Exception as e:
            QMessageBox.warning(self, "Tanınan Cihaz", f"Cihaz adı değiştirilemedi:\n{e}")

    def refresh_current_ui_state(self):
        """Profil değişimi/sıfırlama sonrası uygulamayı kapatmadan ekranları yeniler."""
        try:
            self.apply_theme()
            self.refresh_dynamic_button_styles()
        except Exception:
            pass

        try:
            if hasattr(self, "update_page_combo"):
                current_idx = self.combo_page.currentIndex() if hasattr(self, "combo_page") else 0
                self.update_page_combo()
                if hasattr(self, "combo_page"):
                    self.combo_page.setCurrentIndex(max(0, min(current_idx, self.combo_page.count() - 1)))
        except Exception:
            pass

        for method_name in [
            "refresh_screen_buttons",
            "update_screen_bg",
            "refresh_audio_app_combos",
            "refresh_profile_combo",
        ]:
            try:
                if hasattr(self, method_name):
                    getattr(self, method_name)()
            except Exception:
                pass

        try:
            if hasattr(self, "lbl_current_assignment") and getattr(self, "current_signal", None):
                cfg = self.config.get("buttons", {}).get(self.current_signal, {})
                self.lbl_current_assignment.setText(f"{tr('current_assign')} {cfg.get('name', tr('empty'))}")
        except Exception:
            pass

        try:
            if hasattr(self, "screen_macro_panel"):
                self.screen_macro_panel.setEnabled(False)
        except Exception:
            pass

        try:
            state.APP_CONFIG.update(self.config)
        except Exception:
            pass

    def auto_connect_device(self):
        """Uygulama açılınca NexDeck portu bulunursa otomatik bağlanır."""
        if self.config.get("app_mode", "device") == "web":
            return  # 2.6: cihazsız kullanım
        if not self.config.get("auto_connect", True):
            return
        if self.serial_thread and self.serial_thread.is_running:
            return
        try:
            port = self.find_preferred_port()
            if port:
                self.connect_device(port)
            else:
                # Cihaz henüz takılı değilse takıldığında otomatik bağlan.
                self.reconnect_timer.start(3000)
        except Exception as e:
            try:
                ui_log(f"Otomatik bağlantı başarısız: {e}")
            except Exception:
                pass

    def refresh_profile_combo(self):
        if not hasattr(self, "combo_profile"):
            return
        self.combo_profile.blockSignals(True)
        self.combo_profile.clear()
        ensure_profiles(self.config, update_active=False)
        active = self.config.get("active_profile", DEFAULT_PROFILE_NAME)
        for name in self.config.get("profiles", {}).keys():
            self.combo_profile.addItem(name, name)
        idx = self.combo_profile.findData(active)
        if idx >= 0:
            self.combo_profile.setCurrentIndex(idx)
        self.combo_profile.blockSignals(False)

    def persist_current_profile(self):
        ensure_profiles(self.config, update_active=False)
        active = self.config.get("active_profile", DEFAULT_PROFILE_NAME)
        self.config["profiles"][active] = snapshot_profile_data(self.config)

    def switch_to_profile(self, profile_name):
        profile_name = (profile_name or "").strip()
        if not profile_name:
            return
        ensure_profiles(self.config, update_active=False)
        if profile_name not in self.config.get("profiles", {}):
            return
        self.persist_current_profile()
        self.config["active_profile"] = profile_name
        apply_active_profile(self.config)
        save_config(self.config)
        self.refresh_current_ui_state()
        self.show_saved_feedback(f"Profil yüklendi: {profile_name}")
        if hasattr(self, "combo_profile"):
            self.refresh_profile_combo()
        QTimer.singleShot(300, self.sync_nextion_texts)

    def handle_profile_action(self, action):
        """Cihaz tuşundan/ekrandan gelen profil değiştirme görevleri (GUI thread'inde çalışır)."""
        names = list(self.config.get("profiles", {}).keys())
        if not names:
            return
        current = self.config.get("active_profile", names[0])
        mode = action.get("mode")
        if mode == "switch":
            target = action.get("custom_arg", "")
            if target not in names:
                ui_log(f"⚠️ Profil bulunamadı: {target}")
                return
        else:
            idx = names.index(current) if current in names else 0
            step = 1 if mode == "next" else -1
            target = names[(idx + step) % len(names)]
        if target == current:
            return
        self.switch_to_profile(target)
        ui_log(f"👤 Aktif profil: {target}")
        if self.isHidden() and getattr(self, "tray_icon", None):
            self.tray_icon.showMessage("NexStudio", f"Profil: {target}", QSystemTrayIcon.Information, 1500)

    def change_profile(self):
        if not hasattr(self, "combo_profile"):
            return
        profile_name = self.combo_profile.currentData()
        if profile_name and profile_name != self.config.get("active_profile"):
            self.switch_to_profile(profile_name)

    def create_profile(self):
        name, ok = QInputDialog.getText(self, "Yeni Profil", "Profil adı:", QLineEdit.Normal, "")
        if not ok:
            return
        name = name.strip()
        if not name:
            return
        ensure_profiles(self.config, update_active=True)
        if name in self.config["profiles"]:
            QMessageBox.warning(self, "Profil Var", "Bu isimde bir profil zaten var.")
            return
        self.config["profiles"][name] = {
            "buttons": copy.deepcopy(FACTORY_DEFAULT_BUTTONS),
            "encoder": {"turn": "general_volume"},
            "page_names": {},
            "screen_bg": ""
        }
        self.config["active_profile"] = name
        apply_active_profile(self.config)
        save_config(self.config)
        self.refresh_current_ui_state()
        self.show_saved_feedback(f"Profil oluşturuldu: {name}")

    def copy_profile(self):
        current = self.config.get("active_profile", DEFAULT_PROFILE_NAME)
        name, ok = QInputDialog.getText(self, "Profili Kopyala", "Yeni profil adı:", QLineEdit.Normal, f"{current} Kopya")
        if not ok:
            return
        name = name.strip()
        if not name:
            return
        ensure_profiles(self.config, update_active=True)
        if name in self.config["profiles"]:
            QMessageBox.warning(self, "Profil Var", "Bu isimde bir profil zaten var.")
            return
        self.config["profiles"][name] = copy.deepcopy(self.config["profiles"].get(current, snapshot_profile_data(self.config)))
        self.config["active_profile"] = name
        apply_active_profile(self.config)
        save_config(self.config)
        self.refresh_current_ui_state()
        self.show_saved_feedback(f"Profil kopyalandı: {name}")

    def delete_profile(self):
        ensure_profiles(self.config, update_active=True)
        current = self.config.get("active_profile", DEFAULT_PROFILE_NAME)
        if len(self.config.get("profiles", {})) <= 1:
            QMessageBox.warning(self, "Silinemez", "En az bir profil kalmalı.")
            return
        cevap = QMessageBox.question(self, "Profili Sil", f"'{current}' profilini silmek istiyor musun?", QMessageBox.Yes | QMessageBox.No)
        if cevap != QMessageBox.Yes:
            return
        self.config["profiles"].pop(current, None)
        next_profile = next(iter(self.config["profiles"].keys()))
        self.config["active_profile"] = next_profile
        apply_active_profile(self.config)
        save_config(self.config)
        self.refresh_current_ui_state()
        self.show_saved_feedback(f"Profil silindi. Aktif profil: {next_profile}")

    def change_language(self):
        new_lang = self.combo_lang.currentData()
        if new_lang != self.config.get("language", "tr"):
            self.config["language"] = new_lang
            save_config(self.config)
            self.refresh_current_ui_state()
            self.show_saved_feedback("Aktif profil fabrika ayarlarına döndürüldü")

    def factory_reset(self):
        cevap = QMessageBox.question(self, tr("confirm"), tr("reset_confirm"), QMessageBox.Yes | QMessageBox.No)
        if cevap == QMessageBox.Yes:
            # Sadece aktif profili sıfırla; uygulamayı kapat/aç yapma.
            self.config["buttons"] = copy.deepcopy(FACTORY_DEFAULT_BUTTONS)
            self.config["encoder"] = {"turn": "general_volume"}
            self.config["page_names"] = {}
            self.config["screen_bg"] = ""

            try:
                self.persist_current_profile()
            except Exception:
                ensure_profiles(self.config, update_active=True)

            self.reset_nextion_texts()
            save_config(self.config)
            self.refresh_current_ui_state()
            self.show_saved_feedback("Aktif profil fabrika ayarlarına döndürüldü")


    def restart_app(self):
        save_config(self.config)
        if self.serial_thread:
            self.serial_thread.stop()
            try: self.serial_thread.wait(1500)
            except Exception: pass
        if self.mobile_thread:
            self.mobile_thread.stop()
            try: self.mobile_thread.wait(1500)
            except Exception: pass
        release_single_instance()
        QApplication.quit()
        if getattr(sys, "frozen", False):
            subprocess.Popen([sys.executable] + sys.argv[1:])
        else:
            subprocess.Popen([sys.executable] + sys.argv)

    # ---------------------------------------------------------
    # Cihaz bağlantısı (2.0)
    # ---------------------------------------------------------
    NEXDECK_VIDS = ["2341", "1A86", "0403", "10C4", "1B4F", "2A03"]

    def scan_device_ports(self):
        """NexDeck olabilecek portları döndürür: [(etiket, port, seri_no)]."""
        found = []
        for p in serial.tools.list_ports.comports():
            vid = f"{p.vid:04X}".upper() if p.vid else ""
            desc = p.description or ""
            if vid in self.NEXDECK_VIDS or "Arduino" in desc:
                name = self.config.get("device_names", {}).get(p.serial_number or p.device, "NexDeck")
                found.append((f"{name} · {p.device}", p.device, p.serial_number or ""))
        return found

    def refresh_ports(self):
        current = self.port_combo.currentData() if self.port_combo.count() else None
        self.port_combo.blockSignals(True)
        self.port_combo.clear()
        self._port_serials = {}
        ports = self.scan_device_ports()
        for label, device, serial_no in ports:
            self.port_combo.addItem(label, device)
            self._port_serials[device] = serial_no
        if not ports:
            self.port_combo.addItem(tr("device_not_found"), None)
        else:
            wanted = current or self.find_preferred_port(ports)
            idx = self.port_combo.findData(wanted)
            if idx >= 0:
                self.port_combo.setCurrentIndex(idx)
        self.port_combo.blockSignals(False)

    def find_preferred_port(self, ports=None):
        """Son kullanılan cihazı önce seri numarasıyla (COM numarası değişse bile), sonra port adıyla bulur."""
        ports = ports if ports is not None else self.scan_device_ports()
        if not ports:
            return None
        last_serial = self.config.get("last_port_serial", "")
        if last_serial:
            for _, device, serial_no in ports:
                if serial_no == last_serial:
                    return device
        last_port = self.config.get("last_port", "")
        for _, device, _ in ports:
            if device == last_port:
                return device
        return ports[0][1]

    def is_device_connected(self):
        return bool(self.serial_thread and self.serial_thread.is_running)

    def set_device_status(self, state, detail=""):
        styles = {
            "connected": ("status_connected", "color: #22C55E; background-color: #052E1A; border: 1px solid #14532D;"),
            "waiting": ("status_waiting", "color: #94A3B8; background-color: #111827; border: 1px solid #263244;"),
            "lost": (None, "color: #F59E0B; background-color: #2A1A05; border: 1px solid #78350F;"),
            "searching": (None, "color: #93C5FD; background-color: #0B1A33; border: 1px solid #1E3A8A;"),
        }
        key, css = styles.get(state, styles["waiting"])
        fallback = {"lost": "Bağlantı koptu · yeniden deneniyor", "searching": "Cihaz aranıyor…"}
        text = tr(key) if key else fallback.get(state, "")
        if detail:
            text = f"{text} · {detail}"
        if hasattr(self, "lbl_sidebar_status"):
            self.lbl_sidebar_status.setText(text)
            self.lbl_sidebar_status.setStyleSheet(css + " border-radius: 16px; padding: 8px 12px; font-size: 12px; font-weight: 900;")
        connected = state == "connected"
        self.btn_connect.setText(tr("disconnect") if connected else tr("connect"))
        self.btn_connect.setObjectName("DisconnectBtn" if connected else "ConnectBtn")
        self.btn_connect.style().unpolish(self.btn_connect)
        self.btn_connect.style().polish(self.btn_connect)

    def connect_device(self, port):
        if not port:
            return
        if self.serial_thread:
            self.disconnect_device(user_requested=False)
        self.config["last_port"] = port
        serial_no = getattr(self, "_port_serials", {}).get(port, "")
        if serial_no:
            self.config["last_port_serial"] = serial_no
        save_config(self.config)
        self.device_supports_hid = False
        self.device_supports_ping = False
        self.device_fw = ""
        self._user_disconnected = False
        thread = SerialThread(port)
        thread.data_received.connect(self.handle_serial_data)
        thread.connection_error.connect(self.on_serial_connection_error)
        thread.connected.connect(self.on_serial_connected)
        self.serial_thread = thread
        thread.start()

    def disconnect_device(self, user_requested=True):
        thread = self.serial_thread
        self.serial_thread = None
        if thread:
            try:
                thread.data_received.disconnect()
                thread.connection_error.disconnect()
                thread.connected.disconnect()
            except Exception:
                pass
            thread.stop()
            thread.wait(1500)
        self.device_supports_hid = False
        self.device_supports_ping = False
        if user_requested:
            self._user_disconnected = True
            self.reconnect_timer.stop()
            self.set_device_status("waiting")
            ui_log(f"[-] {tr('disconnect')}")

    def toggle_connection(self):
        if self.is_device_connected():
            self.disconnect_device(user_requested=True)
        else:
            self.connect_device(self.port_combo.currentData())

    def on_serial_connected(self, port):
        self.reconnect_timer.stop()
        self._was_connected = True
        self._last_conn_error = None
        self._shown_lost = False
        self.set_device_status("connected", port)
        ui_log(tr("connected_log") + f" ({port})")
        QTimer.singleShot(2500, self.sync_nextion_texts)

    def on_serial_connection_error(self, error_text):
        """Kablo çıktı / port açılamadı: kullanıcıyı uyar, otomatik yeniden bağlanmayı başlat."""
        was_connected = getattr(self, "_was_connected", False)
        self.disconnect_device(user_requested=False)
        # Yeniden deneme sırasında aynı hata tekrar tekrar günlüğü doldurmasın.
        if error_text != getattr(self, "_last_conn_error", None):
            ui_log(f"⚠️ Cihaz bağlantısı: {error_text}")
            if "PermissionError" in error_text or "Erişim engellendi" in error_text:
                ui_log("ℹ️ Port başka bir program tarafından kullanılıyor (Arduino IDE seri monitör, eski NexStudio vb.).")
        self._last_conn_error = error_text
        if was_connected:
            self._was_connected = False
            if getattr(self, "tray_icon", None):
                self.tray_icon.showMessage("NexStudio", "NexDeck bağlantısı koptu. Otomatik yeniden bağlanılacak.", QSystemTrayIcon.Warning, 3000)
        if self.config.get("auto_connect", True) and not getattr(self, "_user_disconnected", False):
            self.set_device_status("lost" if was_connected or getattr(self, "_shown_lost", False) else "searching")
            self._shown_lost = self._shown_lost if hasattr(self, "_shown_lost") else False
            if was_connected:
                self._shown_lost = True
            if not self.reconnect_timer.isActive():
                self.reconnect_timer.start(3000)
        else:
            self.set_device_status("waiting")

    def set_app_mode(self, mode):
        """2.6: 'device' (NexDeck ile) ya da 'web' (cihazsız, telefon sanal NexDeck)."""
        if mode not in ("device", "web"):
            raise ValueError("Bilinmeyen mod")
        self.config["app_mode"] = mode
        save_config(self.config)
        if mode == "web":
            self.disconnect_device(user_requested=True)
            self.auto_start_web_control()
            ui_log("📱 Web moduna geçildi: telefon sanal NexDeck olarak kullanılıyor")
        else:
            self._user_disconnected = False
            self.refresh_ports()
            port = self.find_preferred_port()
            if port:
                self.connect_device(port)
            else:
                self.set_device_status("searching")
                self.reconnect_timer.start(3000)
            ui_log("🔌 Cihazlı moda geçildi")

    def try_reconnect(self):
        if self.config.get("app_mode", "device") == "web":
            self.reconnect_timer.stop()
            return
        if self.is_device_connected() or getattr(self, "_user_disconnected", False):
            self.reconnect_timer.stop()
            return
        port = self.find_preferred_port()
        if port:
            self.refresh_ports()
            if getattr(self, "_last_conn_error", None) is None:
                ui_log(f"🔄 Yeniden bağlanılıyor: {port}")
            self.connect_device(port)

    def check_device_heartbeat(self):
        """2.0 firmware PING'e PONG ile cevap verir; cevap kesilirse bağlantı kopmuş sayılır."""
        thread = self.serial_thread
        if not thread or not thread.is_running or not getattr(self, "device_supports_ping", False):
            return
        if time.monotonic() - thread.last_rx > 9:
            self.on_serial_connection_error("Cihaz 9 saniyedir cevap vermiyor.")
            return
        thread.send_data("PING\n")

    def handle_device_hello(self, data):
        """'NEXDECK:READY;FW=2.0;CAP=HID,PING' gibi kimlik satırlarını işler."""
        info = {}
        for part in data.split(";")[1:]:
            if "=" in part:
                k, v = part.split("=", 1)
                info[k.strip().upper()] = v.strip()
        caps = [c.strip().upper() for c in info.get("CAP", "").split(",") if c.strip()]
        self.device_fw = info.get("FW", "1.x")
        self.device_supports_hid = "HID" in caps
        self.device_supports_ping = "PING" in caps
        cap_text = ", ".join(caps) if caps else "temel"
        ui_log(f"🔌 NexDeck tanındı · firmware {self.device_fw} · özellikler: {cap_text}")

    def _send_nextion_commands(self, commands, delay):
        """Ekran komutlarını arka thread'de, aralarında bekleyerek gönderir (arayüz donmaz)."""
        thread = self.serial_thread
        if not thread or not thread.is_running or not commands:
            return

        def _job():
            for cmd in commands:
                if not thread.is_running:
                    return
                thread.send_data(cmd)
                time.sleep(delay)

        TASK_WORKER.submit(_job, droppable=False)

    def reset_nextion_texts(self):
        """Sayfa 3-4 özel yazılarını cihaz ekranında temizler."""
        commands = []
        for page_num, obj_list in NEXTION_TEXT_RESET_OBJS.items():
            for obj_name in obj_list:
                commands.append(f'NEXCMD:page{page_num}.{obj_name}.txt=""\n')
        self._send_nextion_commands(commands, 0.03)

    def sync_nextion_texts(self):
        # Sayfa 3-4'te kayıtlı özel yazıları cihaza tekrar bas.
        commands = []
        for page_num, slot_map in NEXTION_TEXT_OBJ_BY_SLOT.items():
            signal_map = TOUCH_UI_SLOT_TO_SIGNAL.get(page_num, {})
            for slot_idx, obj_name in slot_map.items():
                sig = signal_map.get(slot_idx)
                if not sig:
                    continue
                cfg = self.config.get("buttons", {}).get(sig, {})
                btn_text = str(cfg.get("btn_text", "") or "").replace('"', "'").replace("\n", " ")
                if btn_text:
                    commands.append(f'NEXCMD:page{page_num}.{obj_name}.txt="{btn_text}"\n')
        self._send_nextion_commands(commands, 0.05)

    def handle_serial_data(self, data):
        if data.startswith("NEXDECK:"):
            self.handle_device_hello(data)
            return
        if data == "PONG" or data.startswith("HID_OK"):
            return
        if data.startswith("HID_ERR"):
            ui_log(f"⚠️ Cihaz klavye hatası: {data}")
            return

        # 2.5: Arayüzlere canlı gösterim için olay kuyruğu
        self._live_seq += 1
        self._live_events.append((self._live_seq, data))

        if data not in ["ENC:UP", "ENC:DOWN"]:
            ui_log(f"{tr('log_signal')} {data}")

        if should_ignore_serial_signal(data):
            return

        if data in ["ENC:UP", "ENC:DOWN"]:
            # Hızlı çevirmede gelen seri sinyalleri tek tek uygulamak yerine
            # kısa bir tamponda topluyoruz. Bu, yukarı/aşağı zıplamayı ve
            # Windows ses karıştırıcısının kararsız tepki vermesini azaltır.
            self.encoder_pending_steps += 1 if data == "ENC:UP" else -1
            if not self.encoder_flush_timer.isActive():
                self.encoder_flush_timer.start(35)
            return

        # Aynı sinyal 150 ms içinde tekrar gelirse (temas sıçraması / çift gönderim) yok say.
        now = time.monotonic()
        last_sig, last_time = getattr(self, "_last_signal", ("", 0.0))
        if data == last_sig and now - last_time < 0.15:
            return
        self._last_signal = (data, now)

        buttons_cfg = self.config.get("buttons", {})
        resolved_data = resolve_nextion_signal(data, buttons_cfg)
        if resolved_data != data and state.MAIN_WINDOW:
            ui_log(f"{tr('log_signal')} {data} → {resolved_data}")

        cfg = buttons_cfg.get(resolved_data)
        if cfg and cfg.get("action"):
            if state.MAIN_WINDOW: ui_log(tr("found_task").format(cfg.get("name")))
            execute_macro(cfg["action"])
        else:
            if state.MAIN_WINDOW: ui_log(tr("no_assigned_task"))

    def format_audio_app_label(self, proc_name, display_name=""):
        """
        Windows ses oturumlarından gelen uygulama adını kullanıcı dostu hale getirir.
        Değer olarak yine gerçek process adı kullanılır; sadece UI etiketi güzelleştirilir.
        Örn: steam.exe -> Steam, chrome.exe -> Google Chrome.
        """
        raw_proc = (proc_name or "").strip()
        raw_display = (display_name or "").strip()

        def is_windows_resource_name(value):
            value = (value or "").strip().lower()
            return (
                value.startswith("@")
                or ".dll" in value
                or "audiosrv" in value
                or "audioendpointbuilder" in value
                or "windows audio" in value
            )

        # DisplayName çoğu zaman @%SystemRoot%\System32\AudioSrv.Dll,-202 gibi sistem resource metni.
        # Bu durumda asla label kaynağı olarak kullanma.
        if raw_display and not is_windows_resource_name(raw_display) and raw_display.lower() != raw_proc.lower():
            base = raw_display
        else:
            base = raw_proc

        base = base.replace(chr(92), "/").split("/")[-1]
        if "|" in base:
            base = base.split("|")[0].strip()
        if "," in base and ".dll" in base.lower():
            base = ""

        lower = base.lower()
        for ext in [".exe", ".app", ".bat", ".cmd"]:
            if lower.endswith(ext):
                base = base[:-len(ext)]
                break

        known_names = {
            "steam": "Steam",
            "chrome": "Google Chrome",
            "msedge": "Microsoft Edge",
            "edge": "Microsoft Edge",
            "firefox": "Mozilla Firefox",
            "discord": "Discord",
            "spotify": "Spotify",
            "vlc": "VLC Media Player",
            "obs64": "OBS Studio",
            "obs32": "OBS Studio",
            "obs": "OBS Studio",
            "code": "Visual Studio Code",
            "devenv": "Visual Studio",
            "explorer": "Windows Explorer",
            "teams": "Microsoft Teams",
            "ms-teams": "Microsoft Teams",
            "zoom": "Zoom",
            "telegram": "Telegram",
            "whatsapp": "WhatsApp",
            "brave": "Brave",
            "opera": "Opera",
            "opera_gx": "Opera GX",
            "operagx": "Opera GX",
            "winamp": "Winamp",
            "foobar2000": "foobar2000",
            "python": "Python",
            "pythonw": "Python",
        }

        key = base.strip().lower().replace(" ", "_")
        if key in known_names:
            return known_names[key]

        cleaned = re.sub(r"[_\-]+", " ", base).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)

        if not cleaned:
            return raw_proc or "Unknown App"

        if cleaned.islower() or cleaned.isupper():
            cleaned = cleaned.title()

        cleaned = cleaned.replace("Qtwebengineprocess", "Qt WebEngine")
        cleaned = cleaned.replace("Applicationframehost", "Application Frame Host")
        return cleaned

    def get_audio_mixer_apps(self):
        """Windows Ses Karıştırıcısı'nda görünen aktif ses oturumlarını listeler."""
        apps = []
        seen = set()

        def clean_proc_candidate(value):
            value = (value or "").strip()
            if not value:
                return ""

            value_lower = value.lower()

            # Windows resource stringleri uygulama değildir:
            # @%SystemRoot%\System32\AudioSrv.Dll,-202 gibi değerleri tamamen ele.
            if (
                value_lower.startswith("@")
                or "audiosrv.dll" in value_lower
                or "audioendpointbuilder.dll" in value_lower
                or re.search(r"\.dll\s*,\s*-?\d+", value_lower)
                or re.search(r"\{[0-9a-f\.\-]+\}", value_lower)
                or value_lower.startswith("{")
                or "}.{".replace(" ", "") in value_lower
            ):
                return ""

            # InstanceIdentifier/IconPath gibi alanlarda tam path veya | ayracı gelebilir.
            value = value.replace(chr(92), "/")

            # Metnin herhangi bir yerinde gerçek .exe varsa onu yakala.
            exe_matches = re.findall(r"([A-Za-z0-9_\-. ]+\.exe)", value, flags=re.IGNORECASE)
            if exe_matches:
                return exe_matches[-1].strip()

            if "/" in value:
                value = value.split("/")[-1]

            if "|" in value:
                value = value.split("|")[0].strip()

            # DLL hiçbir zaman uygulama kontrol hedefi olmasın.
            if ".dll" in value.lower():
                return ""

            return value.strip()

        def add_app(proc_name, display_name=""):
            proc_name = clean_proc_candidate(proc_name)
            if not proc_name:
                return

            lower_proc = proc_name.lower()
            if (
                lower_proc in ["audiodg.exe", "system sounds", "system", ""]
                or ".dll" in lower_proc
                or lower_proc.startswith("@")
                or lower_proc.startswith("{")
                or "{" in lower_proc
                or "}" in lower_proc
                or "audiosrv" in lower_proc
                or "audioendpointbuilder" in lower_proc
            ):
                return

            # Ses kontrol hedefi olarak en güvenlisi gerçek process exe'leri.
            # InstanceIdentifier gibi exe içermeyen teknik session id'leri listeleme.
            if not lower_proc.endswith(".exe"):
                return

            key = lower_proc
            if key in seen:
                return
            seen.add(key)

            label = self.format_audio_app_label(proc_name, display_name)
            apps.append((label, f"app_volume:{proc_name}"))

        if HAS_PYCAW:
            try:
                import comtypes
                comtypes.CoInitialize()

                sessions = AudioUtilities.GetAllSessions()
                for session in sessions:
                    proc_name = ""
                    display_name = ""

                    try:
                        proc = getattr(session, "Process", None)
                        if proc:
                            try:
                                proc_name = proc.name() or ""
                            except Exception:
                                proc_name = ""
                    except Exception:
                        proc_name = ""

                    if not proc_name:
                        try:
                            pid = getattr(session, "ProcessId", None)
                            if pid:
                                try:
                                    import psutil
                                    proc_name = psutil.Process(int(pid)).name()
                                except Exception:
                                    proc_name = ""
                        except Exception:
                            proc_name = ""

                    try:
                        display_name = getattr(session, "DisplayName", "") or ""
                    except Exception:
                        display_name = ""

                    if not proc_name:
                        proc_name = clean_proc_candidate(display_name)

                    if not proc_name:
                        try:
                            ident = getattr(session, "InstanceIdentifier", "") or ""
                            proc_name = clean_proc_candidate(ident)
                        except Exception:
                            proc_name = ""

                    if not proc_name:
                        try:
                            icon_path = getattr(session, "IconPath", "") or ""
                            proc_name = clean_proc_candidate(icon_path)
                        except Exception:
                            proc_name = ""

                    add_app(proc_name, display_name)

            except Exception:
                pass
            finally:
                try:
                    comtypes.CoUninitialize()
                except Exception:
                    pass

        saved_turn = self.config.get("encoder", {}).get("turn", "")
        if isinstance(saved_turn, str) and saved_turn.startswith("app_volume:"):
            proc_name = saved_turn.split(":", 1)[1].strip()
            saved_key = clean_proc_candidate(proc_name).lower()
            if (
                saved_key
                and saved_key not in seen
                and saved_key.endswith(".exe")
                and "{" not in saved_key
                and "}" not in saved_key
                and ".dll" not in saved_key
            ):
                apps.append((tr("saved_app_suffix").format(self.format_audio_app_label(proc_name)), saved_turn))

        return sorted(apps, key=lambda x: x[0].lower())

    def populate_encoder_combo(self, combo, selected_value=None):
        if combo is None:
            return
        selected_value = selected_value or self.config.get("encoder", {}).get("turn", "general_volume")
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(tr("general_vol"), "general_volume")
        combo.addItem(tr("active_vol"), "active_window")
        combo.addItem(tr("brightness"), "brightness")
        combo.insertSeparator(combo.count())
        combo.addItem(tr("app_vol_header"), "__disabled_header__")
        apps = self.get_audio_mixer_apps()
        if apps:
            for label, value in apps:
                combo.addItem(label, value)
        else:
            combo.addItem(tr("no_audio_apps"), "__no_audio_apps__")

        idx = combo.findData(selected_value)
        if idx < 0 and isinstance(selected_value, str) and selected_value.startswith("app_volume:"):
            proc_name = selected_value.split(":", 1)[1]
            combo.addItem(tr("saved_app_suffix").format(self.format_audio_app_label(proc_name)), selected_value)
            idx = combo.findData(selected_value)
        if idx < 0:
            idx = combo.findData("general_volume")
        if idx >= 0:
            combo.setCurrentIndex(idx)
        combo.blockSignals(False)

    def refresh_audio_app_combos(self):
        current_turn = self.config.get("encoder", {}).get("turn", "general_volume")
        if hasattr(self, "combo_encoder_turn_phys"):
            self.populate_encoder_combo(self.combo_encoder_turn_phys, current_turn)
        if hasattr(self, "combo_encoder_turn"):
            self.populate_encoder_combo(self.combo_encoder_turn, current_turn)
        if state.MAIN_WINDOW and hasattr(state.MAIN_WINDOW, "log_area"):
            ui_log(tr("audio_apps_refresh_log"))

    def save_encoder_value(self, value, text=""):
        if value in ["__disabled_header__", "__no_audio_apps__", None]:
            return False
        if "encoder" not in self.config:
            self.config["encoder"] = {}
        self.config["encoder"]["turn"] = value
        save_config(self.config)
        if text and state.MAIN_WINDOW:
            ui_log(tr("encoder_changed_log").format(text))
        return True

    def process_encoder_pending_steps(self):
        steps = self.encoder_pending_steps
        self.encoder_pending_steps = 0
        if steps == 0:
            return

        enc_cfg = self.config.get("encoder", {})
        self.apply_volume_steps(enc_cfg.get("turn", "general_volume"), steps)

    def apply_volume_steps(self, turn_action, steps):
        """Tekerlek adımlarını hedefe uygular (genel ses, aktif pencere, parlaklık ya da bir uygulama).
        2.7.0: ekstra sanal tekerlekler de bunu kendi hedefleriyle çağırır."""
        delta = max(-0.20, min(0.20, steps * 0.01))  # her kademe %1, tek pakette en fazla %20

        # Ses işlemleri (COM/pycaw) arka thread'de; arayüz takılmaz.
        if turn_action in ["general_volume", "Genel Ses Seviyesi", "General Volume"]:
            TASK_WORKER.submit(self.change_master_volume, delta)
        elif turn_action in ["brightness", "Ekran Parlaklığı", "Screen Brightness"]:
            brightness_delta = max(-20, min(20, steps))
            execute_macro({"type": "nircmd", "cmd": f"changebrightness {brightness_delta}"})
        else:
            TASK_WORKER.submit(self.change_app_volume, turn_action, delta)

    def change_master_volume(self, delta):
        if HAS_PYCAW:
            try:
                import comtypes
                comtypes.CoInitialize()
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
                current_vol = volume.GetMasterVolumeLevelScalar()
                volume.SetMasterVolumeLevelScalar(max(0.0, min(1.0, current_vol + delta)), None)
                return
            except Exception as e:
                if state.MAIN_WINDOW:
                    ui_log(tr("master_volume_fallback").format(str(e)))
            finally:
                try:
                    comtypes.CoUninitialize()
                except:
                    pass

        # Yedek: nircmd varsa yaklaşık %1 sistem sesi değiştirir. Yoksa Windows medya tuşu kullanılır.
        if os.path.exists(NIRCMD_PATH):
            execute_macro({"type": "nircmd", "cmd": f"changesysvolume {int(delta * 65535)}"})
        else:
            press_key(VK_VOLUME_UP if delta > 0 else VK_VOLUME_DOWN)

    def save_encoder_setting(self):
        value = self.combo_encoder_turn.currentData()
        if not self.save_encoder_value(value, self.combo_encoder_turn.currentText()):
            return

        # Ayarlar sekmesinden değişince fiziksel tuş sekmesindeki seçim de güncellensin.
        if hasattr(self, "combo_encoder_turn_phys"):
            idx = self.combo_encoder_turn_phys.findData(value)
            if idx >= 0:
                self.combo_encoder_turn_phys.blockSignals(True)
                self.combo_encoder_turn_phys.setCurrentIndex(idx)
                self.combo_encoder_turn_phys.blockSignals(False)

    def save_encoder_setting_from_physical(self):
        value = self.combo_encoder_turn_phys.currentData()
        if not self.save_encoder_value(value, self.combo_encoder_turn_phys.currentText()):
            return

        # Fiziksel tuş sekmesinden değişince Ayarlar sekmesindeki seçim de güncellensin.
        if hasattr(self, "combo_encoder_turn"):
            idx = self.combo_encoder_turn.findData(value)
            if idx >= 0:
                self.combo_encoder_turn.blockSignals(True)
                self.combo_encoder_turn.setCurrentIndex(idx)
                self.combo_encoder_turn.blockSignals(False)

    def change_app_volume(self, turn_action, delta):
        if not HAS_PYCAW:
            if turn_action in ["active_window", "Aktif Pencere Sesi", "Active Window Volume"]:
                execute_macro({"type": "nircmd", "cmd": f"changeappvolume focused {delta}"})
            else:
                app_name = turn_action.split(":", 1)[-1].strip()
                execute_macro({"type": "nircmd", "cmd": f'changeappvolume "{app_name}" {delta}'})
            return

        try:
            import comtypes
            comtypes.CoInitialize()
            sessions = AudioUtilities.GetAllSessions()
            target_pid = None
            app_name = None

            if turn_action in ["active_window", "Aktif Pencere Sesi", "Active Window Volume"]:
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                pid = ctypes.c_ulong()
                ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                target_pid = pid.value
            else:
                app_name = turn_action.split(":", 1)[-1].strip().lower()
                if app_name and not app_name.endswith(".exe"):
                    app_name += ".exe"

            changed = False
            for session in sessions:
                if not session.Process:
                    continue
                proc_name = session.Process.name().lower() if session.Process.name() else ""

                if target_pid and session.Process.pid == target_pid:
                    vol = session.SimpleAudioVolume
                    current_vol = vol.GetMasterVolume()
                    vol.SetMasterVolume(max(0.0, min(1.0, current_vol + delta)), None)
                    changed = True
                    continue

                if app_name and proc_name == app_name:
                    vol = session.SimpleAudioVolume
                    current_vol = vol.GetMasterVolume()
                    vol.SetMasterVolume(max(0.0, min(1.0, current_vol + delta)), None)
                    changed = True
                    continue

            if not changed and state.MAIN_WINDOW:
                ui_log(tr("audio_session_not_found"))

        except Exception as e:
            if state.MAIN_WINDOW:
                ui_log(tr("volume_error").format(str(e)))
        finally:
            try:
                comtypes.CoUninitialize()
            except:
                pass

    def choose_color(self):
        color = QColorDialog.getColor(QColor(self.current_accent()), self, tr("choose_color"))
        if color.isValid():
            self.config["accent_color"] = color.name()
            save_config(self.config)
            self.apply_theme()
            self.refresh_dynamic_button_styles()
            self.show_saved_feedback(tr("saved_short"))

    def reset_accent_color(self):
        self.config["accent_color"] = "#3B82F6"
        save_config(self.config)
        self.apply_theme()
        self.refresh_dynamic_button_styles()
        self.show_saved_feedback(tr("saved_short"))

    def toggle_startup(self):
        self.config["start_with_win"] = not self.config.get("start_with_win", False)
        self.chk_startup.setText("✅ " + tr("start_win") if self.config.get("start_with_win") else "❌ " + tr("start_win"))
        save_config(self.config)
        self.apply_startup_setting()

    def toggle_auto_connect(self):
        self.config["auto_connect"] = not self.config.get("auto_connect", True)
        save_config(self.config)
        if hasattr(self, "chk_auto_connect"):
            self.chk_auto_connect.setText(("✅ " if self.config.get("auto_connect", True) else "❌ ") + "Cihazı otomatik bağla")

    def change_key_send_mode(self):
        self.config["key_send_mode"] = self.combo_key_mode.currentData()
        save_config(self.config)
        self.show_saved_feedback("Tuş gönderim yöntemi kaydedildi")

    def restart_as_admin(self):
        save_config(self.config)
        if relaunch_as_admin():
            self.force_quit()
        else:
            QMessageBox.warning(self, "NexStudio", "Yönetici izni verilmedi.")

    def rename_connected_deck(self):
        port = self.port_combo.currentData()
        if not port:
            QMessageBox.information(self, "NexStudio", "Önce bir NexDeck seçin.")
            return
        key = getattr(self, "_port_serials", {}).get(port) or port
        names = self.config.setdefault("device_names", {})
        name, ok = QInputDialog.getText(self, "Cihazı Adlandır", "Cihaz adı:", QLineEdit.Normal, names.get(key, "NexDeck"))
        if ok and name.strip():
            names[key] = name.strip()
            save_config(self.config)
            self.refresh_ports()

    def open_error_log(self):
        if not os.path.exists(ERROR_LOG_FILE):
            write_error_log("Hata günlüğü oluşturuldu (henüz hata yok).")
        os.startfile(ERROR_LOG_FILE)

    def toggle_bg(self):
        self.config["run_in_bg"] = not self.config.get("run_in_bg", False)
        self.chk_bg.setText("✅ " + tr("run_bg") if self.config.get("run_in_bg") else "❌ " + tr("run_bg"))
        save_config(self.config)

    def apply_startup_setting(self):
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "NexStudio"
        exe_path = sys.argv[0]
        if os.getenv("NEXSTUDIO_DATA_DIR"):
            return  # Test modunda gerçek başlangıç kaydına dokunma.
        if getattr(sys, "frozen", False):
            exe_path = sys.executable  # paketlenmiş exe'nin kesin tam yolu
        try:
            # 2.0: KEY_ALL_ACCESS yerine sadece gereken izin (KEY_SET_VALUE); bazı sistemlerde tam izin reddediliyordu.
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            if self.config.get("start_with_win"): winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{exe_path}"')
            else:
                try: winreg.DeleteValue(key, app_name)
                except: pass
            winreg.CloseKey(key)
        except Exception as e:
            write_error_log(f"Windows başlangıç ayarı yazılamadı: {e!r}")
            ui_log(f"⚠️ {tr('startup_error')} {e}")

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        app_icon = QIcon(APP_ICON_PATH) if os.path.exists(APP_ICON_PATH) else QIcon()
        if not app_icon.isNull():
            self.tray_icon.setIcon(app_icon)
        else:
            pixmap = QPixmap(32, 32)
            pixmap.fill(QColor(self.current_accent()))
            self.tray_icon.setIcon(QIcon(pixmap))

        tray_menu = QMenu()
        show_action = QAction(tr("tray_show"), self)
        show_action.triggered.connect(self.open_preferred_ui)
        tray_menu.addAction(show_action)
        exit_action = QAction(tr("tray_exit"), self)
        exit_action.triggered.connect(self.force_quit)
        tray_menu.addAction(exit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(
            lambda reason: self.open_preferred_ui()
            if reason in [QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger]
            else None
        )
        self.tray_icon.show()

    # ---------------------------------------------------------
    # 2.5: Yeni arayüz penceresi / klasik görünüm
    # ---------------------------------------------------------
    def open_preferred_ui(self):
        if self.config.get("ui_mode", "modern") == "classic":
            self.show_main_window()
        else:
            self.launch_ui_window()

    def launch_ui_window(self):
        if self.ui_process and self.ui_process.poll() is None:
            self._focus_ui_window()
            return
        if getattr(sys, "frozen", False):
            args = [sys.executable, "--ui", self.local_app.app_url]
        else:
            exe = sys.executable
            pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
            args = [pyw if os.path.exists(pyw) else exe, os.path.abspath(sys.argv[0]), "--ui", self.local_app.app_url]
        self._ui_started_at = time.monotonic()
        self.ui_process = subprocess.Popen(args)
        self.ui_watch_timer.start(1000)

    def _focus_ui_window(self):
        """Açık arayüz penceresini öne getirir."""
        pid = self.ui_process.pid if self.ui_process else None
        if not pid:
            return
        user32 = ctypes.windll.user32
        found = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        def _enum(hwnd, _):
            owner = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if owner.value == pid and user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd) > 0:
                found.append(hwnd)
                return False
            return True

        user32.EnumWindows(_enum, 0)
        if found:
            user32.ShowWindow(found[0], 9)  # SW_RESTORE
            user32.SetForegroundWindow(found[0])

    def close_ui_window(self):
        proc = self.ui_process
        self.ui_process = None
        self.ui_watch_timer.stop()
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(3)
            except Exception:
                pass

    def check_ui_process(self):
        proc = self.ui_process
        if not proc or proc.poll() is None:
            return
        code = proc.returncode
        self.ui_process = None
        self.ui_watch_timer.stop()
        if code == 3 or (code != 0 and time.monotonic() - self._ui_started_at < 5):
            ui_log("⚠️ Yeni arayüz açılamadı (WebView2 eksik olabilir); klasik görünüm açılıyor.")
            self.show_main_window()
            return
        if not self.config.get("run_in_bg"):
            self.force_quit()
        elif self.tray_icon:
            self.tray_icon.showMessage("NexStudio", tr("running_bg"), QSystemTrayIcon.Information, 2000)

    def switch_ui_mode(self, mode):
        self.config["ui_mode"] = mode
        save_config(self.config)
        if mode == "classic":
            self.close_ui_window()
            self.show_main_window()
            ui_log("Klasik görünüme geçildi")
        else:
            self.hide()
            self.launch_ui_window()

    def show_main_window(self):
        try:
            # Tray/arka plandan dönerken her zaman normal boyutta açıyoruz.
            # Kullanıcı isterse sonrasında yine manuel olarak tam ekran/maximize yapabilir.
            self.showNormal()
            self.resize(*getattr(self, "_normal_window_size", (1100, 750)))
            self.show()
            self.raise_()
            self.activateWindow()
            QTimer.singleShot(0, self.force_full_repaint)
            QTimer.singleShot(120, self.force_full_repaint)
            QTimer.singleShot(300, self.force_full_repaint)
        except Exception:
            self.show()

    def closeEvent(self, event):
        if self.config.get("run_in_bg"):
            event.ignore()
            try:
                if not self.isMaximized() and not self.isFullScreen():
                    self._normal_window_size = (max(self.width(), 1100), max(self.height(), 750))
            except Exception:
                pass
            self.hide()
            if self.tray_icon:
                self.tray_icon.showMessage("NexStudio", tr("running_bg"), QSystemTrayIcon.Information, 2000)
        else:
            self.force_quit()

    def force_quit(self):
        try:
            if self.tray_icon:
                self.tray_icon.hide()
        except Exception:
            pass
        try:
            self.close_ui_window()
            self.local_app.stop()
        except Exception:
            pass

        if self.mobile_thread:
            try:
                self.mobile_thread.stop()
                self.mobile_thread.wait(1500)
            except Exception:
                pass
            self.mobile_thread = None

        if self.serial_thread:
            try:
                self.serial_thread.stop()
                self.serial_thread.wait(1000)
            except Exception:
                pass
            self.serial_thread = None

        QApplication.quit()

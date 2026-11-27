# NexStudio — NEXSTUDIO ÖZGÜR YAZILIM LİSANSI (NPL-v2), Telif Hakkı (c) 2026 Ali Mert Taşcı / NexHub. Ayrıntılar: LICENSE.txt

"""Yeni arayüzün yerel API'si (AppApi), yerel sunucu ve arayüz penceresi işlemi."""
from . import state
from .core import (  # noqa: F401
    webbrowser,
    ERROR_LOG_FILE,
    LOG_BUFFER,
    get_small_logo_data_uri,
    APP_DIR,
    APP_VERSION,
    BaseHTTPRequestHandler,
    CONFIG_LOCK,
    HAS_QR,
    NEXSTUDIO_CHANGELOG,
    PLUGINS_DIR,
    QTimer,
    TASK_WORKER,
    _is_gui_thread,
    base64,
    copy,
    get_resource_path,
    hashlib,
    is_process_elevated,
    json,
    os,
    qrcode,
    re,
    run_on_ui,
    secrets,
    sys,
    threading,
    time,
    traceback,
    ui_log,
    urllib,
    write_error_log,
)
from .engine import (  # noqa: F401
    DEFAULT_PROFILE_NAME,
    FACTORY_DEFAULT_BUTTONS,
    TOUCH_UI_SLOT_TO_SIGNAL,
    apply_active_profile,
    ensure_profiles,
    execute_macro,
    format_action_details,
    format_assignment_label,
    get_all_macros,
    is_valid_user_task,
    save_config,
    snapshot_profile_data,
)
from .webserver import (  # noqa: F401
    NexStudioHTTPServer,
)
from .i18n import (  # noqa: F401
    LANGUAGES_DIR,
    load_language_packs,
    load_locales,
    tr,
)

# =========================================================
# 8. YENİ ARAYÜZ (2.5) — YEREL API + PENCERE
# Yeni arayüz web_ui/app.html dosyasıdır. Masaüstünde ayrı bir pencere işleminde
# (pywebview / WebView2) açılır ve çekirdekle bu API üzerinden konuşur.
# Aynı HTML, telefondan "NexStudio Web" olarak PIN ile açılır.
# Arayüz çökse bile çekirdek (tuşlar, seri port) çalışmaya devam eder.
# =========================================================
WEB_UI_DIR = get_resource_path("web_ui")
ICONS_DIR = os.path.join(APP_DIR, "icons")
RUNTIME_FILE = os.path.join(APP_DIR, "runtime.json")
APP_API_TOKEN = secrets.token_urlsafe(24)
os.makedirs(ICONS_DIR, exist_ok=True)

DEFAULT_UI_THEME = {"mode": "dark", "accent": "#F2601C", "bg_color": "", "bg_image": "", "glass": 0.86}


def call_on_ui_sync(fn, timeout=15):
    """Bir fonksiyonu GUI thread'inde çalıştırır ve sonucunu bekler (HTTP thread'lerinden kullanılır)."""
    if state.UI_BRIDGE is None or _is_gui_thread():
        return fn()
    done = threading.Event()
    box = {}

    def _wrap():
        try:
            box["value"] = fn()
        except Exception as e:
            box["error"] = e
        finally:
            done.set()

    run_on_ui(_wrap)
    if not done.wait(timeout):
        raise TimeoutError("Arayüz zamanında cevap vermedi")
    if "error" in box:
        raise box["error"]
    return box.get("value")


def call_on_worker_sync(fn, timeout=10):
    """COM (ses) gibi işlemleri görev thread'inde çalıştırıp sonucu bekler."""
    done = threading.Event()
    box = {}

    def _wrap():
        try:
            box["value"] = fn()
        except Exception as e:
            box["error"] = e
        finally:
            done.set()

    TASK_WORKER.submit(_wrap, droppable=False)
    if not done.wait(timeout):
        raise TimeoutError("Görev thread'i zamanında cevap vermedi")
    if "error" in box:
        raise box["error"]
    return box.get("value")


# ---------- Görev ikonları (emoji) ----------
_VK_EMOJI = {0xB3: "⏯️", 0xB0: "⏭️", 0xB1: "⏮️", 0xAD: "🔇", 0xAF: "🔊", 0xAE: "🔉"}
_KEYWORD_EMOJI = [
    ("yayın", "🔴"), ("stream", "🔴"), ("kayd", "⏺️"), ("kayıt", "⏺️"), ("record", "⏺️"),
    ("mikrofon", "🎙️"), ("mic", "🎙️"), ("sahne", "🎬"), ("scene", "🎬"), ("replay", "⏪"),
    ("stüdyo", "🎛️"), ("masaüstü ses", "🔊"), ("sustur", "🔇"), ("mute", "🔇"), ("sağır", "🎧"),
    ("deafen", "🎧"), ("kamera", "📷"), ("ekran paylaş", "🖥️"), ("el kaldır", "✋"), ("sohbet", "💬"),
    ("kırp", "📸"), ("seçerek", "📸"), ("kapat", "⏻"), ("yeniden başlat", "🔄"), ("uyku", "🌙"), ("kilitle", "🔒"), ("ekran görüntü", "📸"),
    ("alıntı", "📸"), ("hesap makine", "🧮"), ("görev yönet", "📊"), ("dosya gezgini", "📁"), ("klasör", "📁"),
    ("indirilen", "📥"), ("belgeler", "📄"), ("kopyala", "📋"), ("yapıştır", "📋"), ("geri al", "↩️"),
    ("kaydet", "💾"), ("terminal", "💻"), ("komut", "💻"), ("profil", "👤"), ("tam ekran", "🔲"),
    ("sola", "⬅️"), ("sağa", "➡️"), ("küçült", "🪟"), ("diğer ekran", "🖥️"), ("youtube", "▶️"), ("kick", "🟩"),
    ("parlaklık", "🔆"), ("ses", "🔊"), ("şarkı", "🎵"), ("karışık", "🔀"), ("tekrarla", "🔁"),
]
_PLUGIN_EMOJI = [("obs", "🎬"), ("spotify", "🎵"), ("discord", "🎧"), ("zoom", "📹"), ("meet", "📹"),
                 ("code", "💻"), ("photoshop", "🎨"), ("premiere", "🎞️"), ("office", "📄"), ("pencere", "🪟"),
                 ("odak", "🎯"), ("sistem", "🛠️"), ("klasör", "📁")]


def action_emoji(category, name, action):
    action = action or {}
    atype = action.get("type", "")
    text = f"{category} {name}".lower()
    if atype == "native" and action.get("vk") in _VK_EMOJI:
        return _VK_EMOJI[action["vk"]]
    if atype in ("custom_app",):
        return "🚀"
    if atype == "custom_web":
        return "🌐"
    if atype == "custom_hotkey":
        return "⌨️"
    if atype == "type_text":
        return "📝"
    for key, em in _KEYWORD_EMOJI:
        if key in text:
            return em
    if atype == "plugin":
        for key, em in _PLUGIN_EMOJI:
            if key in text:
                return em
        return "🧩"
    if atype == "native":
        return "🔢" if "numpad" in text else "⌨️"
    if atype == "web":
        return "🌐"
    return "✨"


def action_needs(action):
    return {"custom_web": "web", "custom_app": "app", "custom_hotkey": "hotkey", "type_text": "text", "web": "browser"}.get(
        (action or {}).get("type", ""), "")


def _save_data_url_image(data_url, max_size, prefix, fmt="PNG"):
    """Tarayıcıdan gelen resmi küçültüp icons/ klasörüne kaydeder, dosya adını döndürür."""
    from PIL import Image
    import io
    header, b64 = data_url.split(",", 1)
    raw = base64.b64decode(b64)
    if len(raw) > 25 * 1024 * 1024:
        raise ValueError("Resim 25 MB'tan büyük olamaz")
    img = Image.open(io.BytesIO(raw))
    img.thumbnail((max_size, max_size))
    if fmt == "JPEG":
        img = img.convert("RGB")
    elif img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")
    out = io.BytesIO()
    img.save(out, fmt, quality=88)
    data = out.getvalue()
    name = f"{prefix}_{hashlib.sha1(data).hexdigest()[:14]}.{'jpg' if fmt == 'JPEG' else 'png'}"
    with open(os.path.join(ICONS_DIR, name), "wb") as f:
        f.write(data)
    return name


def make_qr_data_uri(text):
    if not HAS_QR or not text:
        return ""
    import io
    qr = qrcode.QRCode(version=None, box_size=8, border=2)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    out = io.BytesIO()
    img.save(out, "PNG")
    return "data:image/png;base64," + base64.b64encode(out.getvalue()).decode("ascii")


HARDWARE_GUIDE_URL = "https://github.com/4llyW3rt/NexDeck/blob/main/docs/DONANIM.md"


def APP_CONFIG_LANG():
    return state.APP_CONFIG.get("language", "tr")


class AppApi:
    """Yeni arayüzün kullandığı JSON API. remote=True: telefondan (LAN) gelen istek, kısıtlı yetki."""

    LOCAL_ONLY = {"device", "web", "known_device", "ui", "settings", "bg_image", "theme", "logs"}

    @classmethod
    def dispatch(cls, method, endpoint, body, remote=False):
        if remote and endpoint in cls.LOCAL_ONLY:
            return 403, {"ok": False, "error": "Bu işlem sadece bilgisayardan yapılabilir."}
        handler = getattr(cls, f"{method.lower()}_{endpoint}", None)
        if handler is None:
            return 404, {"ok": False, "error": f"Bilinmeyen işlem: {endpoint}"}
        try:
            result = handler(body or {}, remote)
            return 200, result if isinstance(result, dict) else {"ok": True}
        except (ValueError, PermissionError) as e:
            # Kullanıcı kaynaklı hata (ör. boş profil adı): günlüğe Traceback yazmaya gerek yok
            return 400, {"ok": False, "error": str(e)}
        except Exception as e:
            write_error_log(f"API hatası ({method} {endpoint}):\n" + traceback.format_exc())
            return 500, {"ok": False, "error": str(e)}

    # ----- okuma -----
    @classmethod
    def get_state(cls, body, remote):
        cfg = state.APP_CONFIG
        win = state.MAIN_WINDOW
        lang = cfg.get("language", "tr")
        library = []
        for cat, actions in get_all_macros().items():
            items = []
            for name, action in actions.items():
                items.append({"name": name, "emoji": action_emoji(cat, name, action), "needs": action_needs(action)})
            library.append({"cat": cat, "items": items})
        buttons = {}
        for sig, bcfg in (cfg.get("buttons") or {}).items():
            if not is_valid_user_task(bcfg):
                continue
            action = bcfg.get("action") or {}
            buttons[sig] = {
                "name": bcfg.get("name", ""),
                "emoji": bcfg.get("emoji") or action_emoji(bcfg.get("category", ""), bcfg.get("name", ""), action),
                "icon": bcfg.get("icon", ""),
                "details": format_action_details(action),
                "needs": action_needs(action),
                "arg": action.get("custom_arg", ""),
                "browser": action.get("browser", "default"),
                "app_action": action.get("app_action", "open"),
                "btn_text": bcfg.get("btn_text", ""),
            }
        slots = {str(p): [m.get(i) for i in range(8)] for p, m in TOUCH_UI_SLOT_TO_SIGNAL.items()}
        result = {
            "ok": True,
            "version": APP_VERSION,
            "remote": remote,
            "lang": lang,
            "profiles": list((cfg.get("profiles") or {}).keys()),
            "active_profile": cfg.get("active_profile", DEFAULT_PROFILE_NAME),
            "buttons": buttons,
            "page_names": cfg.get("page_names", {}),
            "slots": slots,
            "encoder_turn": (cfg.get("encoder") or {}).get("turn", "general_volume"),
            "library": library,
            "theme": {**DEFAULT_UI_THEME, **(cfg.get("ui_theme") or {})},
            "changelog": NEXSTUDIO_CHANGELOG.get(lang, NEXSTUDIO_CHANGELOG["en"]),
            "app_mode": cfg.get("app_mode", "device"),
            "first_run": bool(state.FIRST_RUN) and not cfg.get("welcome_done"),
            "languages": [{"code": c, "name": p["name"]} for c, p in load_language_packs().items()],
            "web_running": bool(win and win.mobile_thread and win.mobile_thread.is_running),
            "device": {
                "connected": bool(win and win.is_device_connected()),
                "port": getattr(getattr(win, "serial_thread", None), "port", "") if win else "",
                "fw": getattr(win, "device_fw", "") if win else "",
                "hid": bool(getattr(win, "device_supports_hid", False)) if win else False,
            },
        }
        if not remote:
            result["settings"] = {
                "start_with_win": bool(cfg.get("start_with_win")),
                "run_in_bg": bool(cfg.get("run_in_bg")),
                "auto_connect": bool(cfg.get("auto_connect", True)),
                "key_send_mode": cfg.get("key_send_mode", "auto"),
                "elevated": is_process_elevated(),
                "dev_mode": bool(cfg.get("dev_mode")),
            }
            result["device"]["ports"] = [{"label": label, "port": port} for label, port, _ in (win.scan_device_ports() if win else [])]
        return result

    @classmethod
    def get_live(cls, body, remote):
        """Arayüzün sık sorduğu hafif uç: son sinyaller (tuş/tekerlek) ve bağlantı durumu."""
        win = state.MAIN_WINDOW
        if not win:
            return {"ok": True, "seq": 0, "events": [], "connected": False}
        try:
            since = int(body.get("since", -1))
        except (TypeError, ValueError):
            since = -1
        seq = win._live_seq
        events = [] if since < 0 else [d for s, d in list(win._live_events) if s > since]
        return {"ok": True, "seq": seq, "events": events, "connected": win.is_device_connected()}

    @classmethod
    def get_logs(cls, body, remote):
        """Geliştirici modu: canlı günlük (since'ten sonraki satırlar) + hata günlüğünün sonu."""
        try:
            since = int(body.get("since", 0))
        except (TypeError, ValueError):
            since = 0
        lines = [{"seq": s, "time": t, "text": m} for s, t, m in list(LOG_BUFFER) if s > since]
        result = {"ok": True, "lines": lines, "seq": lines[-1]["seq"] if lines else since}
        if body.get("errors"):
            try:
                with open(ERROR_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                    result["errors"] = f.read()[-20000:]
            except FileNotFoundError:
                result["errors"] = ""
        return result

    @classmethod
    def get_lang(cls, body, remote):
        """Yeni arayüzün çeviri tablosu (Türkçe metin -> çeviri)."""
        code = body.get("code") or APP_CONFIG_LANG()
        pack = load_language_packs().get(code, {"name": code, "ui": {}})
        return {"ok": True, "code": code, "name": pack["name"], "ui": pack["ui"]}

    @classmethod
    def get_audio_apps(cls, body, remote):
        win = state.MAIN_WINDOW
        apps = call_on_worker_sync(lambda: win.get_audio_mixer_apps()) if win else []
        options = [{"value": "general_volume", "label": "Genel ses"},
                   {"value": "active_window", "label": "Aktif pencerenin sesi"},
                   {"value": "brightness", "label": "Ekran parlaklığı"}]
        options += [{"value": value, "label": label} for label, value in (apps or [])]
        return {"ok": True, "options": options}

    @classmethod
    def get_web(cls, body, remote):
        win = state.MAIN_WINDOW
        running = bool(win and win.mobile_thread and win.mobile_thread.is_running)
        url = getattr(win, "current_web_url", "") if running else ""
        pin = state.APP_CONFIG.get("mobile_pin", "") if running else ""
        devices = []
        for dev_id, d in (state.APP_CONFIG.get("known_web_devices") or {}).items():
            if isinstance(d, dict) and d.get("trusted"):
                devices.append({"id": dev_id, "name": d.get("name") or d.get("device_label") or "Cihaz",
                                "last_seen": d.get("last_seen", "")})
        return {"ok": True, "running": running, "url": url, "pin": pin,
                "qr": make_qr_data_uri(url) if url else "", "devices": devices}

    # ----- tuş atama -----
    @classmethod
    def post_assign(cls, body, remote):
        sig = str(body.get("sig", ""))
        cat, act = body.get("cat", ""), body.get("act", "")
        macros = get_all_macros()
        if not sig or cat not in macros or act not in macros[cat]:
            raise ValueError("Görev bulunamadı")
        action = copy.deepcopy(macros[cat][act])
        atype = action.get("type")
        if atype in ("custom_web", "custom_app", "custom_hotkey", "type_text"):
            action["custom_arg"] = str(body.get("arg", "")).strip()
        if atype in ("custom_web", "web"):
            action["browser"] = body.get("browser", "default") if body.get("browser") in ("default", "chrome", "edge", "firefox") else "default"
        if atype == "custom_app":
            action["app_action"] = body.get("app_action", "open") if body.get("app_action") in ("open", "close", "force_close") else "open"
        with CONFIG_LOCK:
            old = (state.APP_CONFIG.get("buttons") or {}).get(sig) or {}
            entry = {"name": act, "category": cat, "action": action, "details": format_action_details(action),
                     "emoji": action_emoji(cat, act, action)}
            # Aynı göreve ayar değiştirilirken seçilmiş resim korunur
            if old.get("icon") and old.get("name") == act:
                entry["icon"] = old["icon"]
            if sig.startswith("NEX:P3_") or sig.startswith("NEX:P4_"):
                entry["btn_text"] = str(body.get("btn_text", old.get("btn_text", "")))[:20]
            state.APP_CONFIG.setdefault("buttons", {})[sig] = entry
            save_config(state.APP_CONFIG)
        cls._refresh_classic(sync_screen=sig.startswith("NEX:P3_") or sig.startswith("NEX:P4_"))
        return {"ok": True}

    @classmethod
    def post_clear(cls, body, remote):
        sig = str(body.get("sig", ""))
        with CONFIG_LOCK:
            (state.APP_CONFIG.get("buttons") or {}).pop(sig, None)
            save_config(state.APP_CONFIG)
        cls._refresh_classic(sync_screen=sig.startswith("NEX:P3_") or sig.startswith("NEX:P4_"))
        return {"ok": True}

    @classmethod
    def post_test(cls, body, remote):
        cfg = (state.APP_CONFIG.get("buttons") or {}).get(str(body.get("sig", "")))
        if not is_valid_user_task(cfg):
            raise ValueError("Bu tuşa görev atanmamış")
        ui_log(f"▶ {'Telefondan' if remote else 'Arayüzden'} çalıştırıldı: {cfg.get('name')}")
        execute_macro(cfg["action"])
        return {"ok": True}

    @classmethod
    def post_icon(cls, body, remote):
        sig = str(body.get("sig", ""))
        with CONFIG_LOCK:
            cfg = (state.APP_CONFIG.get("buttons") or {}).get(sig)
            if not is_valid_user_task(cfg):
                raise ValueError("Önce bu tuşa bir görev ata")
            if body.get("data"):
                cfg["icon"] = _save_data_url_image(body["data"], 160, "icon")
            elif body.get("emoji"):
                cfg["emoji"] = str(body["emoji"])[:8]
                cfg.pop("icon", None)
            else:
                cfg.pop("icon", None)
            save_config(state.APP_CONFIG)
        return {"ok": True, "icon": cfg.get("icon", "")}

    @classmethod
    def post_page_name(cls, body, remote):
        page = str(body.get("page", ""))
        if page not in ("1", "2", "3", "4"):
            raise ValueError("Geçersiz sayfa")
        with CONFIG_LOCK:
            state.APP_CONFIG.setdefault("page_names", {})[page] = str(body.get("name", "")).strip()[:20]
            save_config(state.APP_CONFIG)
        cls._refresh_classic()
        return {"ok": True}

    @classmethod
    def post_encoder(cls, body, remote):
        turn = str(body.get("turn", ""))
        if not turn:
            raise ValueError("Tekerlek ayarı boş")
        with CONFIG_LOCK:
            state.APP_CONFIG.setdefault("encoder", {})["turn"] = turn
            save_config(state.APP_CONFIG)
        cls._refresh_classic()
        return {"ok": True}

    @classmethod
    def post_volume(cls, body, remote):
        steps = max(-20, min(20, int(body.get("steps", 0))))
        win = state.MAIN_WINDOW
        if win and steps:
            run_on_ui(lambda: (setattr(win, "encoder_pending_steps", win.encoder_pending_steps + steps),
                               win.process_encoder_pending_steps()))
        return {"ok": True}

    # ----- profiller -----
    @classmethod
    def post_profile(cls, body, remote):
        op = body.get("op")
        name = str(body.get("name", "")).strip()[:40]
        win = state.MAIN_WINDOW
        if op == "switch":
            if name not in (state.APP_CONFIG.get("profiles") or {}):
                raise ValueError("Profil bulunamadı")
            call_on_ui_sync(lambda: win.switch_to_profile(name))
            return {"ok": True}
        if remote:
            raise PermissionError("Profil oluşturma/silme sadece bilgisayardan yapılabilir.")

        def _apply():
            ensure_profiles(win.config, update_active=True)
            profiles = win.config["profiles"]
            current = win.config.get("active_profile")
            if op in ("create", "copy"):
                if not name:
                    raise ValueError("Profil adı boş olamaz")
                if name in profiles:
                    raise ValueError("Bu isimde bir profil zaten var")
                profiles[name] = (copy.deepcopy(profiles.get(current, snapshot_profile_data(win.config))) if op == "copy" else
                                  {"buttons": copy.deepcopy(FACTORY_DEFAULT_BUTTONS), "encoder": {"turn": "general_volume"},
                                   "page_names": {}, "screen_bg": ""})
                win.config["active_profile"] = name
            elif op == "rename":
                new_name = str(body.get("new_name", "")).strip()[:40]
                if not new_name or new_name in profiles:
                    raise ValueError("Geçersiz ya da kullanılan profil adı")
                profiles[new_name] = profiles.pop(name)
                if current == name:
                    win.config["active_profile"] = new_name
            elif op == "delete":
                if len(profiles) <= 1:
                    raise ValueError("En az bir profil kalmalı")
                profiles.pop(name, None)
                if current == name:
                    win.config["active_profile"] = next(iter(profiles))
            else:
                raise ValueError("Bilinmeyen profil işlemi")
            apply_active_profile(win.config)
            save_config(win.config)
            win.refresh_current_ui_state()
            win.refresh_profile_combo()
            QTimer.singleShot(300, win.sync_nextion_texts)

        call_on_ui_sync(_apply)
        return {"ok": True}

    # ----- ayarlar (sadece bilgisayar) -----
    @classmethod
    def post_settings(cls, body, remote):
        key, value = body.get("key"), body.get("value")
        win = state.MAIN_WINDOW
        if key not in ("start_with_win", "run_in_bg", "auto_connect", "key_send_mode", "language", "app_mode", "welcome_done", "dev_mode"):
            raise ValueError("Bilinmeyen ayar")
        if key == "app_mode":
            call_on_ui_sync(lambda: win.set_app_mode(value))
            return {"ok": True}
        if key == "language" and value not in load_language_packs():
            raise ValueError("Bu dil yüklü değil")

        def _apply():
            win.config[key] = value
            save_config(win.config)
            if key == "start_with_win":
                win.apply_startup_setting()
            if key == "language":
                load_locales()
                win.refresh_current_ui_state()

        call_on_ui_sync(_apply)
        return {"ok": True}

    @classmethod
    def post_theme(cls, body, remote):
        with CONFIG_LOCK:
            theme = {**DEFAULT_UI_THEME, **(state.APP_CONFIG.get("ui_theme") or {})}
            if body.get("mode") in ("dark", "light"):
                theme["mode"] = body["mode"]
            if re.match(r"^#[0-9A-Fa-f]{6}$", str(body.get("accent", ""))):
                theme["accent"] = body["accent"]
            if "bg_color" in body and (body["bg_color"] == "" or re.match(r"^#[0-9A-Fa-f]{6}$", str(body["bg_color"]))):
                theme["bg_color"] = body["bg_color"]
            if "glass" in body:
                theme["glass"] = max(0.3, min(1.0, float(body["glass"])))
            state.APP_CONFIG["ui_theme"] = theme
            save_config(state.APP_CONFIG)
        return {"ok": True, "theme": theme}

    @classmethod
    def post_bg_image(cls, body, remote):
        with CONFIG_LOCK:
            theme = {**DEFAULT_UI_THEME, **(state.APP_CONFIG.get("ui_theme") or {})}
            theme["bg_image"] = _save_data_url_image(body["data"], 2560, "bg", fmt="JPEG") if body.get("data") else ""
            state.APP_CONFIG["ui_theme"] = theme
            save_config(state.APP_CONFIG)
        return {"ok": True, "theme": theme}

    @classmethod
    def post_device(cls, body, remote):
        win = state.MAIN_WINDOW
        op = body.get("op")

        def _apply():
            win.refresh_ports()
            if op == "connect":
                win.connect_device(body.get("port") or win.find_preferred_port())
            elif op == "disconnect":
                win.disconnect_device(user_requested=True)

        call_on_ui_sync(_apply)
        return {"ok": True}

    @classmethod
    def post_web(cls, body, remote):
        win = state.MAIN_WINDOW
        op = body.get("op")

        def _apply():
            running = bool(win.mobile_thread and win.mobile_thread.is_running)
            if op == "start" and not running or op == "stop" and running:
                win.toggle_mobile_server()
            elif op == "reset" and running:
                win.reset_web_sessions()

        call_on_ui_sync(_apply)
        time.sleep(0.4)  # sunucunun açılması için kısa bekleme
        return cls.get_web({}, remote)

    @classmethod
    def post_known_device(cls, body, remote):
        dev_id = str(body.get("id", ""))
        with CONFIG_LOCK:
            devices = state.APP_CONFIG.get("known_web_devices") or {}
            if dev_id not in devices:
                raise ValueError("Cihaz bulunamadı")
            if body.get("op") == "forget":
                devices.pop(dev_id, None)
            elif body.get("op") == "rename":
                devices[dev_id]["name"] = str(body.get("name", "")).strip()[:40]
            save_config(state.APP_CONFIG)
        run_on_ui(lambda: state.MAIN_WINDOW.refresh_web_security_panel())
        return {"ok": True}

    @classmethod
    def post_ui(cls, body, remote):
        op = body.get("op")
        win = state.MAIN_WINDOW
        if op == "classic":
            call_on_ui_sync(lambda: win.switch_ui_mode("classic"))
        elif op == "show":
            run_on_ui(win.open_preferred_ui)
        elif op == "open_plugins":
            os.startfile(PLUGINS_DIR)
        elif op == "open_languages":
            os.startfile(LANGUAGES_DIR)
        elif op == "open_guide":
            webbrowser.open(HARDWARE_GUIDE_URL)
        elif op == "open_logs":
            run_on_ui(win.open_error_log)
        elif op == "admin":
            run_on_ui(win.restart_as_admin)
        elif op == "quit":
            run_on_ui(win.force_quit)
        else:
            raise ValueError("Bilinmeyen işlem")
        return {"ok": True}

    @staticmethod
    def _refresh_classic(sync_screen=False):
        win = state.MAIN_WINDOW
        if not win:
            return

        def _do():
            try:
                win.refresh_screen_buttons()
                if getattr(win, "current_signal", None) and hasattr(win, "lbl_current_assignment"):
                    cfg = win.config.get("buttons", {}).get(win.current_signal, {})
                    win.lbl_current_assignment.setText(f"{tr('current_assign')} {format_assignment_label(cfg) if cfg else tr('empty')}")
                if sync_screen:
                    win.sync_nextion_texts()
            except Exception:
                pass

        run_on_ui(_do)


def read_app_html(api_base, remote, auth_query=""):
    """web_ui/app.html dosyasını okuyup başlangıç ayarlarını ekler."""
    with open(os.path.join(WEB_UI_DIR, "app.html"), "r", encoding="utf-8") as f:
        html = f.read()
    boot = json.dumps({"apiBase": api_base, "remote": remote, "auth": auth_query, "logo": get_small_logo_data_uri()})
    return html.replace("/*__NEX_BOOT__*/", f"window.NEX_BOOT = {boot};")


def send_bytes(handler, data, content_type, status=200, extra_headers=None):
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(data)))
    for k, v in (extra_headers or {}).items():
        handler.send_header(k, v)
    handler.end_headers()
    handler.wfile.write(data)


def send_icon_file(handler, name):
    name = os.path.basename(urllib.parse.unquote(name))
    path = os.path.join(ICONS_DIR, name)
    if not re.match(r"^(icon|bg)_[0-9a-f]{14}\.(png|jpg)$", name) or not os.path.exists(path):
        return send_bytes(handler, b"", "text/plain", 404)
    with open(path, "rb") as f:
        data = f.read()
    send_bytes(handler, data, "image/png" if name.endswith(".png") else "image/jpeg",
               extra_headers={"Cache-Control": "max-age=31536000, immutable"})


def read_json_body(handler, limit=30 * 1024 * 1024):
    length = int(handler.headers.get("Content-Length", "0") or 0)
    if length > limit:
        raise ValueError("İstek çok büyük")
    raw = handler.rfile.read(length) if length else b"{}"
    return json.loads(raw.decode("utf-8") or "{}")


class LocalAppHandler(BaseHTTPRequestHandler):
    """Sadece 127.0.0.1: masaüstü arayüz penceresi. Rastgele oturum anahtarı ile korunur."""

    def log_message(self, format, *args):
        return

    def _authorized(self):
        cookie = self.headers.get("Cookie", "") or ""
        header = self.headers.get("X-Nex-Token", "")
        return header == APP_API_TOKEN or f"nex_app={APP_API_TOKEN}" in cookie

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if parsed.path == "/app" and params.get("t", [""])[0] == APP_API_TOKEN:
            # Anahtarı çereze yazıp adres çubuğundan temizle
            self.send_response(302)
            self.send_header("Set-Cookie", f"nex_app={APP_API_TOKEN}; Path=/; HttpOnly; SameSite=Strict")
            self.send_header("Location", "/app")
            self.end_headers()
            return
        if not self._authorized():
            return send_bytes(self, "Yetkisiz".encode("utf-8"), "text/plain; charset=utf-8", 403)
        if parsed.path == "/app":
            return send_bytes(self, read_app_html("/api2", False).encode("utf-8"), "text/html; charset=utf-8")
        if parsed.path.startswith("/icons/"):
            return send_icon_file(self, parsed.path[len("/icons/"):])
        if parsed.path.startswith("/api2/"):
            query = {k: v[0] for k, v in params.items()}
            status, payload = AppApi.dispatch("GET", parsed.path[len("/api2/"):], query, remote=False)
            return send_bytes(self, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", status)
        send_bytes(self, b"", "text/plain", 404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if not self._authorized() or not parsed.path.startswith("/api2/"):
            return send_bytes(self, "Yetkisiz".encode("utf-8"), "text/plain; charset=utf-8", 403)
        try:
            body = read_json_body(self)
        except Exception as e:
            return send_bytes(self, json.dumps({"ok": False, "error": str(e)}).encode("utf-8"), "application/json", 400)
        status, payload = AppApi.dispatch("POST", parsed.path[len("/api2/"):], body, remote=False)
        send_bytes(self, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", status)


class LocalAppServer:
    def __init__(self):
        self.server = NexStudioHTTPServer(("127.0.0.1", 0), LocalAppHandler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.3},
                                       name="NexLocalApp", daemon=True)
        self.thread.start()
        try:
            with open(RUNTIME_FILE, "w", encoding="utf-8") as f:
                json.dump({"port": self.port, "token": APP_API_TOKEN, "pid": os.getpid()}, f)
        except Exception:
            pass

    @property
    def app_url(self):
        return f"http://127.0.0.1:{self.port}/app?t={APP_API_TOKEN}"

    def stop(self):
        try:
            self.server.shutdown()
            self.server.server_close()
        except Exception:
            pass
        try:
            os.remove(RUNTIME_FILE)
        except Exception:
            pass


def notify_running_instance():
    """İkinci kez açılınca: çalışan NexStudio'ya 'pencereni göster' der. Başarılıysa True."""
    try:
        with open(RUNTIME_FILE, "r", encoding="utf-8") as f:
            info = json.load(f)
        import urllib.request
        req = urllib.request.Request(f"http://127.0.0.1:{info['port']}/api2/ui", data=b'{"op":"show"}',
                                     headers={"X-Nex-Token": info["token"], "Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=3).read()
        return True
    except Exception:
        return False


def run_ui_window_process(url):
    """'--ui <adres>' ile başlatılan pencere işlemi: sadece arayüzü gösterir, çekirdek ayrı işlemdedir."""
    try:
        import webview
    except Exception:
        sys.exit(3)

    class Bridge:
        def pick_file(self):
            win = webview.windows[0]
            result = win.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False,
                                            file_types=("Uygulamalar (*.exe;*.lnk;*.bat;*.url)", "Tüm dosyalar (*.*)"))
            return result[0] if result else ""

    try:
        webview.create_window("NexStudio", url, width=1320, height=840, min_size=(980, 640),
                              background_color="#171A21", js_api=Bridge())
        webview.start(gui="edgechromium", private_mode=False,
                      storage_path=os.path.join(APP_DIR, "webview"))
    except Exception:
        write_error_log("Arayüz penceresi açılamadı:\n" + traceback.format_exc())
        sys.exit(3)
    sys.exit(0)

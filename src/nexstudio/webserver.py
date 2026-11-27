# NexStudio — NEXSTUDIO ÖZGÜR YAZILIM LİSANSI (NPL-v2), Telif Hakkı (c) 2026 Ali Mert Taşcı / NexHub. Ayrıntılar: LICENSE.txt

"""Telefondan kontrol (LAN) web sunucusu: PIN, tanınan cihazlar, eski web arayüzü."""
from . import state
from .core import (  # noqa: F401
    threading,
    CONFIG_LOCK,
    QSystemTrayIcon,
    run_on_ui,
    BaseHTTPRequestHandler,
    LOGS_DIR,
    QThread,
    TASK_WORKER,
    ThreadingHTTPServer,
    WEB_HISTORY_LIMIT,
    datetime,
    find_nexstudio_logo_path,
    get_nexstudio_logo_html,
    glob,
    hashlib,
    json,
    os,
    pyqtSignal,
    re,
    run_on_ui,
    secrets,
    socket,
    time,
    traceback,
    ui_log,
    urllib,
    write_error_log,
)
from .engine import (  # noqa: F401
    DEFAULT_MOBILE_PORT,
    TOUCH_UI_SLOT_TO_SIGNAL,
    execute_macro,
    get_all_macros,
    get_physical_buttons,
    save_config,
)
from .state import lazy as _lazy

# =========================================================
# 5. MOBİL SUNUCU (WEB ARAYÜZÜ)
# =========================================================
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


def cleanup_old_log_files(days=7):
    """APPDATA/NexStudio/logs içindeki 7 günden eski günlük dosyalarını temizler."""
    try:
        cutoff = time.time() - (days * 24 * 60 * 60)
        for file_path in glob.glob(os.path.join(LOGS_DIR, "*.txt")):
            try:
                if os.path.getmtime(file_path) < cutoff:
                    os.remove(file_path)
            except Exception:
                pass
    except Exception:
        pass


def _today_log_file():
    return os.path.join(LOGS_DIR, f"nexstudio_log_{datetime.now().strftime('%Y-%m-%d')}.txt")


def write_log_file(message):
    try:
        if not os.path.exists(LOGS_DIR):
            os.makedirs(LOGS_DIR)
        line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {str(message)}\n"
        with open(_today_log_file(), "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def append_system_log(message):
    """Web sunucusu gibi arka threadlerden gelen güvenlik/servis olaylarını UI'a ve günlük dosyasına yazar."""
    try:
        text = str(message)
        write_log_file(text)
        if state.MAIN_WINDOW and hasattr(state.MAIN_WINDOW, "log_area"):
            ui_log(text)
    except Exception:
        pass


WEB_ACCESS_SESSIONS = {}
WEB_PIN_FAILURES = {}
WEB_BLOCKED_CLIENTS = {}
WEB_PIN_FAIL_LIMIT = 5
WEB_PIN_FAIL_WINDOW_SECONDS = 5 * 60
WEB_PIN_BLOCK_SECONDS = 5 * 60


def mask_ip_for_log(ip):
    try:
        if not state.APP_CONFIG.get("web_private_log", False):
            return ip
        parts = str(ip).split(".")
        if len(parts) == 4:
            return ".".join(parts[:3] + ["xxx"])
        return "gizli-ip"
    except Exception:
        return ip


def make_web_device_id(ip, user_agent):
    raw = f"{ip}|{user_agent or ''}"
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()[:16]


def web_client_info_text(ip, user_agent, include_known_name=True):
    info = parse_web_client_info(user_agent)
    device_id = make_web_device_id(ip, user_agent)
    known = state.APP_CONFIG.get("known_web_devices", {}) if isinstance(state.APP_CONFIG, dict) else {}
    known_data = known.get(device_id, {}) if isinstance(known, dict) else {}
    known_name = known_data.get("name", "") if isinstance(known_data, dict) else ""
    base = f"{info['device_type']} / {info['device_model']} / {info['os_name']} / {info['browser']}"
    if include_known_name and known_name:
        return f"{known_name} | {base}"
    return base


def ensure_known_web_device(ip, user_agent):
    """Başarılı PIN girişinden sonra cihazı tanınan cihaz listesine ekler."""
    try:
        if "known_web_devices" not in state.APP_CONFIG or not isinstance(state.APP_CONFIG.get("known_web_devices"), dict):
            state.APP_CONFIG["known_web_devices"] = {}
        device_id = make_web_device_id(ip, user_agent)
        known = state.APP_CONFIG["known_web_devices"]
        info = parse_web_client_info(user_agent)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if device_id not in known:
            default_name = f"{info['device_type']} - {info['browser']}"
            known[device_id] = {
                "name": default_name,
                "allowed": True,
                "first_seen": now,
                "last_seen": now,
                "ip": ip,
                "user_agent": user_agent,
                "device_type": info.get("device_type", ""),
                "device_model": info.get("device_model", ""),
                "os_name": info.get("os_name", ""),
                "browser": info.get("browser", ""),
            }
        else:
            known[device_id]["last_seen"] = now
            known[device_id]["ip"] = ip
            known[device_id]["user_agent"] = user_agent
            known[device_id]["device_type"] = info.get("device_type", known[device_id].get("device_type", ""))
            known[device_id]["device_model"] = info.get("device_model", known[device_id].get("device_model", ""))
            known[device_id]["os_name"] = info.get("os_name", known[device_id].get("os_name", ""))
            known[device_id]["browser"] = info.get("browser", known[device_id].get("browser", ""))
        return device_id
    except Exception:
        return make_web_device_id(ip, user_agent)


def is_known_web_device_allowed(ip, user_agent, trusted_device_id=""):
    try:
        if not state.APP_CONFIG.get("web_known_only", False):
            return True
        known = state.APP_CONFIG.get("known_web_devices", {})
        if not isinstance(known, dict):
            return False
        for dev in (trusted_device_id, make_web_device_id(ip, user_agent)):
            rec = known.get(dev) if dev else None
            if isinstance(rec, dict) and rec.get("allowed") and not rec.get("blocked"):
                return True
        return False
    except Exception:
        return True


def make_web_trust_hash(token):
    try:
        return hashlib.sha256(str(token or "").encode("utf-8", errors="ignore")).hexdigest()
    except Exception:
        return ""


def find_trusted_web_device_by_token(token):
    """Tarayıcıda saklanan güven anahtarını tanınan cihaz kaydıyla eşleştirir."""
    try:
        token_hash = make_web_trust_hash(token)
        if not token_hash:
            return "", {}
        known = state.APP_CONFIG.get("known_web_devices", {})
        if not isinstance(known, dict):
            return "", {}
        for device_id, data in known.items():
            if isinstance(data, dict) and data.get("trust_hash") == token_hash and data.get("allowed", False):
                return device_id, data
    except Exception:
        pass
    return "", {}


def create_trusted_web_device(ip, user_agent, name=""):
    """Kullanıcı onay verirse cihazı güvenli token ile tanınan cihaz listesine ekler."""
    try:
        if "known_web_devices" not in state.APP_CONFIG or not isinstance(state.APP_CONFIG.get("known_web_devices"), dict):
            state.APP_CONFIG["known_web_devices"] = {}
        info = parse_web_client_info(user_agent)
        trust_token = secrets.token_urlsafe(32)
        trust_hash = make_web_trust_hash(trust_token)
        device_id = "TRUST-" + hashlib.sha256((trust_hash + "|" + str(user_agent)).encode("utf-8", errors="ignore")).hexdigest()[:16]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        clean_name = str(name or "").strip()
        if not clean_name:
            clean_name = f"{info.get('device_type', 'Cihaz')} - {info.get('browser', 'Tarayıcı')}"
        state.APP_CONFIG["known_web_devices"][device_id] = {
            "name": clean_name,
            "allowed": True,
            "trusted": True,
            "trust_hash": trust_hash,
            "first_seen": now,
            "last_seen": now,
            "ip": ip,
            "user_agent": user_agent,
            "device_type": info.get("device_type", ""),
            "device_model": info.get("device_model", ""),
            "os_name": info.get("os_name", ""),
            "browser": info.get("browser", ""),
        }
        save_config(state.APP_CONFIG)
        return trust_token, device_id, state.APP_CONFIG["known_web_devices"][device_id]
    except Exception:
        return "", "", {}


def update_trusted_web_device_seen(device_id, ip, user_agent):
    try:
        known = state.APP_CONFIG.get("known_web_devices", {})
        if not isinstance(known, dict) or device_id not in known:
            return
        info = parse_web_client_info(user_agent)
        known[device_id]["last_seen"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        known[device_id]["ip"] = ip
        known[device_id]["user_agent"] = user_agent
        known[device_id]["device_type"] = info.get("device_type", known[device_id].get("device_type", ""))
        known[device_id]["device_model"] = info.get("device_model", known[device_id].get("device_model", ""))
        known[device_id]["os_name"] = info.get("os_name", known[device_id].get("os_name", ""))
        known[device_id]["browser"] = info.get("browser", known[device_id].get("browser", ""))
        state.APP_CONFIG["known_web_devices"] = known
        save_config(state.APP_CONFIG)
    except Exception:
        pass


def add_web_history(event_type, ip, user_agent, detail="", device_id_override="", device_name_override=""):
    """Web giriş geçmişine kısa kayıt ekler; listede son 250 kayıt tutulur."""
    try:
        if "web_access_history" not in state.APP_CONFIG or not isinstance(state.APP_CONFIG.get("web_access_history"), list):
            state.APP_CONFIG["web_access_history"] = []
        info = parse_web_client_info(user_agent)
        device_id = device_id_override or make_web_device_id(ip, user_agent)
        known = state.APP_CONFIG.get("known_web_devices", {}) if isinstance(state.APP_CONFIG.get("known_web_devices"), dict) else {}
        known_name = device_name_override or (known.get(device_id, {}).get("name", "Bilinmeyen cihaz") if isinstance(known, dict) else "Bilinmeyen cihaz")
        entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "event": str(event_type),
            "device_id": device_id,
            "device_name": known_name,
            "ip": str(ip),
            "ip_display": mask_ip_for_log(ip),
            "detail": str(detail or ""),
            "device_type": info.get("device_type", ""),
            "device_model": info.get("device_model", ""),
            "os_name": info.get("os_name", ""),
            "browser": info.get("browser", ""),
        }
        state.APP_CONFIG["web_access_history"].insert(0, entry)
        state.APP_CONFIG["web_access_history"] = state.APP_CONFIG["web_access_history"][:WEB_HISTORY_LIMIT]
        try: save_config(state.APP_CONFIG)
        except Exception: pass
        try:
            if state.MAIN_WINDOW and hasattr(state.MAIN_WINDOW, "refresh_web_security_panel"):
                run_on_ui(state.MAIN_WINDOW.refresh_web_security_panel)
        except Exception: pass
        return entry
    except Exception:
        return None


def record_web_event(event_type, ip, user_agent, detail="", icon="ℹ️", add_to_history=True, device_id_override=""):
    try:
        known = state.APP_CONFIG.get("known_web_devices", {}) if isinstance(state.APP_CONFIG.get("known_web_devices", {}), dict) else {}
        device_name = ""
        if device_id_override and isinstance(known, dict):
            device_name = known.get(device_id_override, {}).get("name", "")
        client_text = web_client_info_text(ip, user_agent)
        if device_name:
            client_text = f"{device_name} | {client_text}"
        line = f"{icon} {event_type}: {mask_ip_for_log(ip)} | {client_text}"
        if detail: line += f" | {detail}"
        append_system_log(line)
        if add_to_history:
            add_web_history(event_type, ip, user_agent, detail, device_id_override=device_id_override, device_name_override=device_name)
        return line
    except Exception:
        append_system_log(f"{icon} {event_type}: {detail}")
        return ""


def get_pin_block_remaining(ip):
    try:
        until = WEB_BLOCKED_CLIENTS.get(ip, 0)
        remaining = int(until - time.time())
        if remaining > 0:
            return remaining
        WEB_BLOCKED_CLIENTS.pop(ip, None)
        return 0
    except Exception:
        return 0


def register_pin_failure(ip):
    try:
        now = time.time()
        bucket = WEB_PIN_FAILURES.get(ip, [])
        bucket = [t for t in bucket if now - t <= WEB_PIN_FAIL_WINDOW_SECONDS]
        bucket.append(now)
        WEB_PIN_FAILURES[ip] = bucket
        if len(bucket) >= WEB_PIN_FAIL_LIMIT:
            WEB_BLOCKED_CLIENTS[ip] = now + WEB_PIN_BLOCK_SECONDS
            WEB_PIN_FAILURES[ip] = []
            return True
    except Exception:
        pass
    return False


def reset_pin_failures(ip):
    try:
        WEB_PIN_FAILURES.pop(ip, None)
        WEB_BLOCKED_CLIENTS.pop(ip, None)
    except Exception:
        pass


def get_pin_attempts_remaining(ip):
    try:
        now = time.time()
        bucket = WEB_PIN_FAILURES.get(ip, [])
        bucket = [t for t in bucket if now - t <= WEB_PIN_FAIL_WINDOW_SECONDS]
        WEB_PIN_FAILURES[ip] = bucket
        return max(0, WEB_PIN_FAIL_LIMIT - len(bucket))
    except Exception:
        return WEB_PIN_FAIL_LIMIT


def html_escape(text):
    try:
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    except Exception:
        return ""


def parse_web_client_info(user_agent):
    """Tarayıcı User-Agent bilgisinden cihaz türü, işletim sistemi, tarayıcı ve mümkünse model tahmini üretir."""
    ua = str(user_agent or "")
    ua_l = ua.lower()

    if "ipad" in ua_l:
        device_type = "Tablet"
        device_model = "iPad"
    elif "iphone" in ua_l:
        device_type = "Telefon"
        device_model = "iPhone"
    elif "android" in ua_l:
        if "mobile" in ua_l:
            device_type = "Telefon"
        else:
            device_type = "Tablet"
        model_match = re.search(r"Android[^;)]*(?:;\s*[^;)]*)?;\s*([^;)]*?)(?:\s+Build|\)|;)", ua, re.I)
        device_model = model_match.group(1).strip() if model_match else "Android cihaz"
        # Bazı tarayıcılar gerçek modeli "K", "wv" gibi anlamsız kısa değerlerle saklıyor.
        if not device_model or len(device_model) <= 2 or device_model.lower() in ["wv", "mobile", "k"]:
            device_model = "Android cihaz"
    elif "windows" in ua_l:
        device_type = "PC"
        device_model = "Windows PC"
    elif "mac os" in ua_l or "macintosh" in ua_l:
        device_type = "PC"
        device_model = "Mac"
    elif "linux" in ua_l:
        device_type = "PC"
        device_model = "Linux PC"
    else:
        device_type = "Bilinmeyen cihaz"
        device_model = "Model algılanamadı"

    if "edg/" in ua_l or "edga/" in ua_l or "edgios/" in ua_l:
        browser = "Microsoft Edge"
    elif "opr/" in ua_l or "opera" in ua_l:
        browser = "Opera"
    elif "firefox/" in ua_l:
        browser = "Firefox"
    elif "chrome/" in ua_l or "crios/" in ua_l:
        browser = "Chrome"
    elif "safari/" in ua_l:
        browser = "Safari"
    else:
        browser = "Bilinmeyen tarayıcı"

    if "windows" in ua_l:
        os_name = "Windows"
    elif "android" in ua_l:
        android_match = re.search(r"Android\s*([0-9.]+)", ua, re.I)
        os_name = "Android" + (f" {android_match.group(1)}" if android_match else "")
    elif "iphone" in ua_l or "ipad" in ua_l or "cpu os" in ua_l:
        ios_match = re.search(r"OS\s*([0-9_]+)", ua, re.I)
        os_name = "iOS" + (f" {ios_match.group(1).replace('_', '.')}" if ios_match else "")
    elif "mac os" in ua_l or "macintosh" in ua_l:
        os_name = "macOS"
    elif "linux" in ua_l:
        os_name = "Linux"
    else:
        os_name = "Bilinmeyen sistem"

    return {
        "device_type": device_type,
        "device_model": device_model,
        "browser": browser,
        "os_name": os_name,
    }

# =========================================================
# 2.6.3 OTURUMLAR, ENGELLEME, BİLGİSAYARDAN ONAY
# - Başarılı girişten sonra cihaza HttpOnly oturum çerezi verilir; "Bağlantıyı kes" oturumu kapatır.
# - Engellenen cihaz hiçbir sayfaya erişemez.
# - Erişim modu (kullanıcı seçer): "pin" | "approve" (sadece bilgisayardan onay) | "pin_approve" (ikisi birden).
#   Onay bekleyen cihaz 60 sn içinde onaylanmazsa reddedilir.
# =========================================================
WEB_SESSIONS = {}          # oturum anahtarı -> {"device", "ip", "ua", "created", "seen"}
WEB_APPROVED = set()       # bu çalışmada onaylanan cihazlar
WEB_PENDING = {}           # cihaz -> {"id", "name", "info", "since", "decision", "remember", "notified"}
SESSION_COOKIE = "nexstudio_sess"
APPROVAL_TIMEOUT = 60
WEB_ACCESS_MODES = ("pin", "approve", "pin_approve")
_WEB_LOCK = threading.Lock()
_WEB_LAST_SAVE = {}


def web_access_mode():
    mode = state.APP_CONFIG.get("web_access_mode", "pin")
    return mode if mode in WEB_ACCESS_MODES else "pin"


def web_device_record(device_id):
    known = state.APP_CONFIG.get("known_web_devices") or {}
    rec = known.get(device_id) if device_id else None
    return rec if isinstance(rec, dict) else {}


def is_web_device_blocked(*device_ids):
    return any(web_device_record(d).get("blocked") for d in device_ids if d)


def touch_web_device(device_id, ip, user_agent, allowed_default=True):
    """Bağlanan ya da bağlanmaya çalışan cihazı listeye kaydeder, son görülme zamanını günceller."""
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    is_new = False
    with CONFIG_LOCK:
        known = state.APP_CONFIG.setdefault("known_web_devices", {})
        rec = known.get(device_id)
        if not isinstance(rec, dict):
            info = parse_web_client_info(user_agent)
            rec = known[device_id] = {
                "name": f"{info.get('device_type', 'Cihaz')} - {info.get('browser', 'Tarayıcı')}",
                "allowed": bool(allowed_default), "first_seen": now_text, "user_agent": user_agent,
                "device_type": info.get("device_type", ""), "device_model": info.get("device_model", ""),
                "os_name": info.get("os_name", ""), "browser": info.get("browser", ""),
            }
            is_new = True
        rec["last_seen"] = now_text
        rec["ip"] = ip
    # Her istekte diske yazmamak için: yeni cihazda hemen, sonra en fazla dakikada bir
    if is_new or time.time() - _WEB_LAST_SAVE.get(device_id, 0) > 60:
        _WEB_LAST_SAVE[device_id] = time.time()
        save_config(state.APP_CONFIG)
        if state.MAIN_WINDOW:
            run_on_ui(state.MAIN_WINDOW.refresh_web_security_panel)


def create_web_session(device_id, ip, user_agent):
    token_value = secrets.token_urlsafe(24)
    with _WEB_LOCK:
        WEB_SESSIONS[token_value] = {"device": device_id, "ip": ip, "ua": user_agent, "created": time.time(), "seen": time.time()}
    return token_value


def end_web_sessions(device_id):
    with _WEB_LOCK:
        for key in [k for k, s in WEB_SESSIONS.items() if s["device"] == device_id]:
            del WEB_SESSIONS[key]
        WEB_APPROVED.discard(device_id)


def clear_all_web_sessions():
    with _WEB_LOCK:
        WEB_SESSIONS.clear()
        WEB_APPROVED.clear()
        WEB_PENDING.clear()


def online_web_devices(window=45):
    now = time.time()
    with _WEB_LOCK:
        return {s["device"] for s in WEB_SESSIONS.values() if now - s["seen"] < window}


def web_approval_status(device_id, ip, user_agent):
    """Onay isteği oluşturur / durumunu döndürür: None (bekliyor), ('allow', remember), ('deny',), ('timeout',)."""
    now = time.time()
    with _WEB_LOCK:
        req = WEB_PENDING.get(device_id)
        if req and req["decision"] is None and now - req["since"] > APPROVAL_TIMEOUT:
            req["decision"] = "timeout"
        if req and req["decision"] is not None:
            WEB_PENDING.pop(device_id, None)
            if req["decision"] == "allow":
                WEB_APPROVED.add(device_id)
                return ("allow", req.get("remember", False))
            return (req["decision"],)
        if not req:
            rec = web_device_record(device_id)
            WEB_PENDING[device_id] = req = {
                "id": device_id, "name": rec.get("name") or "Yeni cihaz",
                "info": web_client_info_text(ip, user_agent, include_known_name=False),
                "since": now, "decision": None, "remember": False, "notified": False,
            }
        notify = not req["notified"]
        req["notified"] = True
    if notify:
        ui_log(f"🔔 Web: '{req['name']}' bağlanmak istiyor; NexStudio'dan onay bekleniyor")
        win = state.MAIN_WINDOW
        if win and getattr(win, "tray_icon", None):
            run_on_ui(lambda: win.tray_icon.showMessage("NexStudio", f"{req['name']} bağlanmak istiyor. Onaylamak için NexStudio'yu aç.", QSystemTrayIcon.Information, 5000))
    return None


def pending_web_approvals():
    now = time.time()
    with _WEB_LOCK:
        out = []
        for req in WEB_PENDING.values():
            if req["decision"] is None and now - req["since"] <= APPROVAL_TIMEOUT:
                out.append({"id": req["id"], "name": req["name"], "info": req["info"],
                            "remaining": int(APPROVAL_TIMEOUT - (now - req["since"]))})
        return out


def decide_web_approval(device_id, allow, remember=False):
    with _WEB_LOCK:
        req = WEB_PENDING.get(device_id)
        if not req or req["decision"] is not None:
            return False
        req["decision"] = "allow" if allow else "deny"
        req["remember"] = bool(remember)
    ui_log(f"{'✅' if allow else '⛔'} Web: '{req['name']}' {'onaylandı' if allow else 'reddedildi'}")
    return True


class MobileHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # PyInstaller --windowed modunda gereksiz konsol çıktısı üretmesin.
        return

    def _client_ip(self):
        try:
            return self.client_address[0]
        except Exception:
            return "bilinmeyen-ip"

    def _client_user_agent(self):
        try:
            return self.headers.get("User-Agent", "")
        except Exception:
            return ""

    def _get_cookie_value(self, name):
        try:
            cookie_header = self.headers.get("Cookie", "") or ""
            for part in cookie_header.split(";"):
                if "=" not in part:
                    continue
                key, value = part.strip().split("=", 1)
                if key == name:
                    return urllib.parse.unquote(value)
        except Exception:
            pass
        return ""

    def _session_device(self):
        """2.6.3: geçerli oturum çerezi varsa cihaz kimliğini döndürür (son görülmeyi günceller)."""
        key = self._get_cookie_value(SESSION_COOKIE)
        if not key:
            return ""
        with _WEB_LOCK:
            sess = WEB_SESSIONS.get(key)
            if not sess:
                return ""
            sess["seen"] = time.time()
            return sess["device"]

    def _send_waiting_page(self, remaining):
        html = f"""<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="2"><title>NexStudio</title>
<style>body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#171A21;color:#ECEEF3;font-family:Segoe UI,system-ui,sans-serif;text-align:center;padding:24px}}
.b{{max-width:360px}}.s{{width:46px;height:46px;border:4px solid #363C4B;border-top-color:#F2601C;border-radius:50%;margin:0 auto 18px;animation:r 1s linear infinite}}
@keyframes r{{to{{transform:rotate(360deg)}}}}p{{color:#9097A8;line-height:1.5}}</style></head>
<body><div class="b"><div class="s"></div><h2>Onay bekleniyor</h2><p>Bilgisayardaki NexStudio'da bu cihazın bağlanmasına izin verilmesi bekleniyor. Kalan süre: {int(remaining)} sn</p></div></body></html>"""
        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_with_cookies(self, data, content_type, cookies, status=200, location=""):
        self.send_response(status)
        if location:
            self.send_header("Location", location)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        for c in cookies:
            self.send_header("Set-Cookie", c)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _trusted_device_id(self):
        try:
            token_value = self._get_cookie_value("nexstudio_trust")
            if not token_value:
                query = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(query)
                token_value = params.get("trust", [""])[0]
            device_id, _data = find_trusted_web_device_by_token(token_value)
            return device_id
        except Exception:
            return ""

    def _log_web_login_once(self, auth_method="PIN girişi", trusted_device_id=""):
        try:
            ip = self._client_ip()
            ua = self._client_user_agent()
            session_key = f"{ip}|{ua}|{trusted_device_id or 'pin'}"
            now = time.time()
            last_seen = WEB_ACCESS_SESSIONS.get(session_key, 0)
            if now - last_seen < 60:
                return
            WEB_ACCESS_SESSIONS[session_key] = now
            reset_pin_failures(ip)
            if trusted_device_id:
                update_trusted_web_device_seen(trusted_device_id, ip, ua)
                record_web_event("Web girişi yapıldı", ip, ua, "Tanınan cihaz ile PIN'siz giriş", "✅", device_id_override=trusted_device_id)
            else:
                record_web_event("Web girişi yapıldı", ip, ua, "Başarılı PIN girişi - cihaz otomatik tanınmadı", "✅")
        except Exception:
            pass

    def _send_static_file(self, path, content_type):
        try:
            if not path or not os.path.exists(path):
                self.send_response(404); self.end_headers(); return
            with open(path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers(); self.wfile.write(data)
        except Exception as e:
            self._send_plain_text(f"Asset okunamadı: {e}", status=500)

    def _send_json(self, payload, status=200, trust_cookie=""):
        data = json.dumps(payload, ensure_ascii=False).encode('utf-8', errors='replace')
        self.send_response(status)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        if trust_cookie:
            cookie_val = urllib.parse.quote(trust_cookie)
            self.send_header('Set-Cookie', f'nexstudio_trust={cookie_val}; Path=/; Max-Age=31536000; SameSite=Lax')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers(); self.wfile.write(data)


    def _send_login_page(self, token, error_message="", sub_message="", attempts_remaining=None, blocked_remaining=0, status=200):
        accent = state.APP_CONFIG.get('accent_color', '#3B82F6')
        logo_html = get_nexstudio_logo_html()
        error_message = html_escape(error_message)
        sub_message = html_escape(sub_message)
        blocked_remaining = max(0, int(blocked_remaining or 0))
        locked = blocked_remaining > 0
        attempts_html = ""
        if attempts_remaining is not None and not locked:
            attempts_html = f"<div class='attempts'>Kalan deneme: <b>{int(attempts_remaining)}</b> / {WEB_PIN_FAIL_LIMIT}</div>"
        alert_html = ""
        if error_message:
            alert_html = f"<div class='alert {'locked' if locked else 'error'}'><strong>{error_message}</strong><span>{sub_message}</span>{attempts_html}</div>"
        disabled = "disabled" if locked else ""
        timer_script = ""
        if locked:
            timer_script = f"""
            <script>
            let remaining = {blocked_remaining};
            const timerEl = document.getElementById('lock-timer');
            const formEl = document.getElementById('pin-form');
            function fmt(sec) {{
                const m = Math.floor(sec / 60).toString().padStart(2, '0');
                const s = Math.max(0, sec % 60).toString().padStart(2, '0');
                return `${{m}}:${{s}}`;
            }}
            function tick() {{
                if (timerEl) timerEl.textContent = fmt(remaining);
                remaining -= 1;
                if (remaining < 0) {{
                    location.href = '/{token}';
                }} else {{
                    setTimeout(tick, 1000);
                }}
            }}
            if (formEl) formEl.classList.add('locked');
            tick();
            </script>
            """
        html = f"""
        <!DOCTYPE html>
        <html lang="tr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>NexStudio Web Kontrolü</title>
            <style>
            :root {{
                --accent: {accent};
                --bg: #070B14;
                --card: rgba(15, 23, 42, .82);
                --border: rgba(148, 163, 184, .18);
                --text: #F8FAFC;
                --muted: #94A3B8;
                --danger: #EF4444;
                --warning: #F97316;
            }}
            * {{ box-sizing: border-box; }}
            body {{
                min-height: 100vh; margin: 0; color: var(--text);
                font-family: Inter, 'Segoe UI', Roboto, Arial, sans-serif;
                background:
                    radial-gradient(circle at 20% 10%, color-mix(in srgb, var(--accent) 24%, transparent), transparent 34%),
                    radial-gradient(circle at 80% 0%, rgba(139, 92, 246, .22), transparent 32%),
                    linear-gradient(145deg, #050814 0%, #0B1220 50%, #111827 100%);
                display: grid; place-items: center; padding: 22px;
            }}
            .login-card {{
                width: min(430px, 100%);
                background: var(--card);
                border: 1px solid var(--border);
                border-radius: 30px;
                padding: 28px;
                box-shadow: 0 26px 90px rgba(0,0,0,.42);
                backdrop-filter: blur(22px);
                animation: cardIn .24s ease both;
            }}
            @keyframes cardIn {{ from {{ opacity: 0; transform: translateY(10px) scale(.99); }} to {{ opacity: 1; transform: none; }} }}
            .brand {{ display:flex; align-items:center; gap:14px; margin-bottom: 22px; }}
            .logo {{
                width: 58px; height: 58px; border-radius: 18px;
                display:grid; place-items:center;
                background: rgba(255,255,255,.08);
                border: 1px solid rgba(255,255,255,.14);
                overflow:hidden;
                box-shadow: 0 16px 42px rgba(0,0,0,.28);
            }}
            .logo img {{ width:100%; height:100%; object-fit:cover; display:block; }}
            .logo span {{ display:grid; place-items:center; width:100%; height:100%; font-size:22px; font-weight:950; color:#fff; }}
            h2 {{ margin:0; font-size:26px; letter-spacing:-.02em; }}
            p {{ color: var(--muted); margin: 8px 0 24px; line-height:1.55; }}
            .alert {{
                border-radius: 18px;
                padding: 13px 14px;
                margin: 0 0 14px;
                border: 1px solid rgba(239,68,68,.42);
                background: rgba(239,68,68,.12);
                color: #FECACA;
                animation: shake .28s ease;
            }}
            .alert.locked {{
                border-color: rgba(249,115,22,.46);
                background: rgba(249,115,22,.13);
                color: #FED7AA;
                animation: none;
            }}
            .alert strong {{ display:block; font-size:14px; margin-bottom:4px; }}
            .alert span, .attempts {{ display:block; font-size:12px; color: rgba(255,255,255,.78); line-height:1.45; }}
            @keyframes shake {{
                0%,100% {{ transform: translateX(0); }} 25% {{ transform: translateX(-5px); }} 50% {{ transform: translateX(5px); }} 75% {{ transform: translateX(-3px); }}
            }}
            input {{
                width:100%; padding: 18px 16px; border-radius: 18px;
                background: rgba(2, 6, 23, .58); color: white;
                border: 1px solid var(--border); outline: none;
                text-align:center; font-size:22px; letter-spacing: 8px; font-weight: 900;
                text-transform: uppercase; margin-bottom: 14px;
            }}
            input:focus {{ border-color: var(--accent); box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent) 18%, transparent); }}
            input:disabled {{ opacity:.45; cursor:not-allowed; }}
            button {{
                width:100%; border:0; border-radius:18px; padding: 17px 18px;
                background: var(--accent); color:#fff; font-size:16px; font-weight:900;
                cursor:pointer; box-shadow: 0 16px 44px color-mix(in srgb, var(--accent) 30%, transparent);
                transition: transform .18s ease, filter .18s ease, opacity .18s ease;
            }}
            button:active {{ transform: scale(.98); }}
            button:disabled {{ opacity:.45; cursor:not-allowed; transform:none; }}
            .hint {{ font-size: 13px; margin-top: 14px; text-align:center; color: var(--muted); }}
            .timer {{ font-weight: 950; color:#FDBA74; }}
            </style>
        </head>
        <body>
            <main class="login-card">
                <div class="brand">
                    <div class="logo">{logo_html}</div>
                    <div>
                        <h2>NexStudio</h2>
                        <p style="margin:3px 0 0;">Web Kontrolü</p>
                    </div>
                </div>
                <p>Lütfen bilgisayar ekranındaki 6 haneli PIN kodunu girin.</p>
                {alert_html}
                <form id="pin-form" action="/{token}" method="GET">
                    <input type="text" name="pin" placeholder="PIN" maxlength="6" required autocomplete="off" autocapitalize="characters" {disabled} oninput="this.value=this.value.toUpperCase()" autofocus><br>
                    <button type="submit" {disabled}>{'Kilitli · ' if locked else ''}<span id="lock-timer" class="timer"></span>{' sonra tekrar dene' if locked else 'Giriş Yap'}</button>
                </form>
                <div class="hint">Güvenli bağlantı için QR kodu tekrar okutabilirsin.</div>
            </main>
            {timer_script}
        </body>
        </html>
        """
        data = html.encode('utf-8', errors='replace')
        self.send_response(status)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_plain_text(self, text, status=200):
        data = str(text).encode('utf-8', errors='replace')
        self.send_response(status)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_error_page(self, error_text):
        safe_error = str(error_text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        html = f"""
        <!DOCTYPE html>
        <html lang="tr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>NexStudio Web Hatası</title>
            <style>
                body {{ margin:0; min-height:100vh; display:grid; place-items:center; padding:22px; background:#070B14; color:#F8FAFC; font-family:'Segoe UI',Arial,sans-serif; }}
                .card {{ max-width:720px; width:100%; background:#0B1220; border:1px solid #263244; border-radius:24px; padding:22px; box-shadow:0 20px 70px rgba(0,0,0,.35); }}
                h1 {{ margin:0 0 10px; font-size:24px; }}
                p {{ color:#94A3B8; line-height:1.55; }}
                pre {{ white-space:pre-wrap; background:#020617; border:1px solid #1E293B; border-radius:16px; padding:14px; color:#FCA5A5; overflow:auto; }}
            </style>
        </head>
        <body>
            <main class="card">
                <h1>NexStudio Web Kontrolü açılırken hata oluştu</h1>
                <p>Bu ekran boş sayfa yerine gerçek hatayı göstermek için eklendi. Aşağıdaki mesajı bana gönderirsen doğrudan düzeltebiliriz.</p>
                <pre>{safe_error}</pre>
            </main>
        </body>
        </html>
        """
        data = html.encode('utf-8', errors='replace')
        try:
            self.send_response(500)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
        except Exception:
            pass
        try:
            self.wfile.write(data)
        except Exception:
            pass

    def do_GET(self):
        try:
            return self._do_GET_safe()
        except Exception as e:
            if state.MAIN_WINDOW and hasattr(state.MAIN_WINDOW, 'log_area'):
                try:
                    ui_log(f"⚠️ Web arayüz hatası: {e}")
                except Exception:
                    pass
            return self._send_error_page(e)

    def do_POST(self):
        """2.5: NexStudio Web yazma istekleri. PIN 'X-Nex-Pin' başlığında ya da tanınan cihaz çerezi ile."""
        ip, ua = self._client_ip(), self._client_user_agent()
        try:
            token = state.APP_CONFIG.get("web_token", "")
            path = urllib.parse.urlparse(self.path).path
            prefix = f"/{token}/api2/"
            if not token or not path.startswith(prefix):
                record_web_event("Yetkisiz Web Girişi", ip, ua, f"POST {path}", "🚫")
                return self._send_json({"ok": False, "error": "Yetkisiz"}, status=403)
            trusted = self._trusted_device_id() or self._session_device()
            if is_web_device_blocked(trusted, make_web_device_id(ip, ua)):
                return self._send_json({"ok": False, "error": "Bu cihazın erişimi engellendi."}, status=401)
            if not trusted and web_access_mode() != "pin":
                return self._send_json({"ok": False, "error": "Oturum yok. Sayfayı yenileyin."}, status=401)
            if not trusted:
                if get_pin_block_remaining(ip) > 0:
                    return self._send_json({"ok": False, "error": "Çok fazla hatalı PIN. Biraz bekleyin."}, status=429)
                pin = (self.headers.get("X-Nex-Pin", "") or "").strip().upper()
                correct = state.APP_CONFIG.get("mobile_pin", "").strip().upper()
                if not pin or pin != correct:
                    register_pin_failure(ip)
                    record_web_event("Hatalı PIN denemesi", ip, ua, "Yanlış PIN girildi", "🔐")
                    return self._send_json({"ok": False, "error": "PIN hatalı"}, status=401)
            if not is_known_web_device_allowed(ip, ua, trusted):
                return self._send_json({"ok": False, "error": "Bu cihaz tanınan cihazlar listesinde değil."}, status=403)
            body = _lazy('app_api', 'read_json_body')(self, limit=8 * 1024 * 1024)
            status, payload = _lazy('app_api', 'AppApi').dispatch("POST", path[len(prefix):], body, remote=True)
            return self._send_json(payload, status=status)
        except Exception as e:
            write_error_log("Web POST hatası:\n" + traceback.format_exc())
            return self._send_json({"ok": False, "error": str(e)}, status=500)

    def _do_GET_safe(self):
        token = state.APP_CONFIG.get("web_token", "")
        if self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        if not self.path.startswith(f"/{token}"):
            record_web_event("Yetkisiz Web Girişi", self._client_ip(), self._client_user_agent(), f"Yol: {self.path}", "🚫")
            body = "Yetkisiz Erisim! Lutfen NexStudio Web Kontrolu icindeki dogru URL/QR kodu kullanin.".encode("utf-8")
            self.send_response(403)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        parsed_path = urllib.parse.urlparse(self.path).path
        if parsed_path == f"/{token}/assets/logo.png":
            return self._send_static_file(find_nexstudio_logo_path(), "image/png")

        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        pin = params.get('pin', [''])[0].strip().upper()
        correct_pin = state.APP_CONFIG.get("mobile_pin", "").strip().upper()
        trusted_device_id = self._trusted_device_id()
        session_device = self._session_device()
        client_ip, client_ua = self._client_ip(), self._client_user_agent()
        raw_device = make_web_device_id(client_ip, client_ua)
        # 2.6.3: engellenen cihaz
        if is_web_device_blocked(trusted_device_id, session_device, raw_device):
            record_web_event("Engellenen cihaz erişmeye çalıştı", client_ip, client_ua, "", "⛔", add_to_history=False)
            if parsed_path.startswith(f"/{token}/api") or parsed_path.startswith(f"/{token}/icons/"):
                return self._send_json({"ok": False, "error": "Bu cihazın erişimi engellendi."}, status=401)
            return self._send_plain_text("Bu cihazın NexStudio'ya erişimi engellendi.", status=403)
        access_mode = web_access_mode()
        trusted_auth = bool(trusted_device_id or session_device)
        is_api_path = parsed_path.startswith(f"/{token}/api") or parsed_path.startswith(f"/{token}/icons/") or parsed_path.startswith(f"/{token}/exec")
        new_session, extra_cookies = None, []

        if not trusted_auth and access_mode == "approve":
            pass  # sadece onay modu: PIN sorulmaz, aşağıdaki onay kapısından geçilir
        elif not trusted_auth:
            if is_api_path and not pin:
                # Oturumu kapanmış (ya da kesilmiş) yeni arayüz: JSON cevap, arayüz sayfayı yenileyip giriş ekranına düşer
                return self._send_json({"ok": False, "error": "Oturum kapandı. Tekrar bağlanın."}, status=401)
            blocked_remaining = get_pin_block_remaining(self._client_ip())
            if blocked_remaining > 0:
                record_web_event("Geçici engelli web denemesi", self._client_ip(), self._client_user_agent(), f"Kalan süre: {blocked_remaining} sn", "⛔")
                return self._send_login_page(token, error_message="Çok fazla hatalı giriş yapıldı", sub_message="Güvenlik nedeniyle PIN girişi geçici olarak kilitlendi.", blocked_remaining=blocked_remaining, status=429)

            if pin != correct_pin:
                attempts_remaining = None
                if pin:
                    blocked_now = register_pin_failure(self._client_ip())
                    attempts_remaining = get_pin_attempts_remaining(self._client_ip())
                    record_web_event("Hatalı PIN denemesi", self._client_ip(), self._client_user_agent(), "Yanlış PIN girildi", "🔐")
                    if blocked_now:
                        record_web_event("Cihaz geçici engellendi", self._client_ip(), self._client_user_agent(), f"{WEB_PIN_FAIL_LIMIT} hatalı PIN", "⛔")
                        return self._send_login_page(token, error_message="Çok fazla hatalı giriş yapıldı", sub_message="Güvenlik nedeniyle PIN girişi geçici olarak kilitlendi.", blocked_remaining=get_pin_block_remaining(self._client_ip()), status=429)
                return self._send_login_page(token, error_message=("Hatalı PIN kodu" if pin else ""), sub_message=("Lütfen bilgisayar ekranındaki güncel PIN kodunu kontrol edin." if pin else ""), attempts_remaining=attempts_remaining, status=200)
        else:
            reset_pin_failures(self._client_ip())

        # 2.6.3: bilgisayardan onay + oturum açma (sadece sayfa isteğinde; API oturum çerezi ister)
        if not trusted_auth:
            if access_mode in ("approve", "pin_approve"):
                if is_api_path:
                    return self._send_json({"ok": False, "error": "Oturum yok. Sayfayı yenileyin."}, status=401)
                if raw_device not in WEB_APPROVED and not web_device_record(raw_device).get("auto_approve"):
                    touch_web_device(raw_device, client_ip, client_ua, allowed_default=not state.APP_CONFIG.get("web_known_only", False))
                    decision = web_approval_status(raw_device, client_ip, client_ua)
                    if decision is None:
                        req = WEB_PENDING.get(raw_device) or {"since": time.time()}
                        return self._send_waiting_page(APPROVAL_TIMEOUT - (time.time() - req["since"]))
                    if decision[0] != "allow":
                        msg = "Bağlantı isteği reddedildi." if decision[0] == "deny" else "Onay zamanında gelmedi. Tekrar denemek için sayfayı yenileyin."
                        return self._send_plain_text(msg, status=403)
                    if decision[1]:  # "hatırla" seçildi: kalıcı tanınan cihaz çerezi
                        trust_token, trusted_id, _data = create_trusted_web_device(client_ip, client_ua, web_device_record(raw_device).get("name", ""))
                        if trust_token:
                            extra_cookies.append(f"nexstudio_trust={urllib.parse.quote(trust_token)}; Path=/; Max-Age=31536000; HttpOnly; SameSite=Lax")
                            with CONFIG_LOCK:
                                (state.APP_CONFIG.get("known_web_devices") or {}).get(raw_device, {})["auto_approve"] = True
            if not is_api_path:
                touch_web_device(raw_device, client_ip, client_ua, allowed_default=not state.APP_CONFIG.get("web_known_only", False))
                new_session = create_web_session(raw_device, client_ip, client_ua)
                extra_cookies.append(f"{SESSION_COOKIE}={new_session}; Path=/; HttpOnly; SameSite=Lax")
        else:
            touch_web_device(trusted_device_id or session_device, client_ip, client_ua)

        if self.path.startswith(f'/{token}/api/trust_device'):
            raw_name = params.get('name', [''])[0]
            name = urllib.parse.unquote_plus(raw_name).strip()
            trust_token, device_id, data = create_trusted_web_device(self._client_ip(), self._client_user_agent(), name)
            if not trust_token:
                return self._send_json({"ok": False, "error": "Cihaz tanınan listeye eklenemedi."}, status=500)
            record_web_event("Cihaz tanındı", self._client_ip(), self._client_user_agent(), f"Ad: {data.get('name', '')}", "✅", device_id_override=device_id)
            return self._send_json({"ok": True, "device_id": device_id, "name": data.get("name", ""), "trust_token": trust_token}, trust_cookie=trust_token)

        # 2.5: NexStudio Web (yeni arayüz) API'si ve ikonlar
        if parsed_path.startswith(f"/{token}/api2/") or parsed_path.startswith(f"/{token}/icons/"):
            if not is_known_web_device_allowed(self._client_ip(), self._client_user_agent(), trusted_device_id):
                return self._send_json({"ok": False, "error": "Bu cihaz tanınan cihazlar listesinde değil."}, status=403)
            if parsed_path.startswith(f"/{token}/icons/"):
                return _lazy('app_api', 'send_icon_file')(self, parsed_path.split("/icons/", 1)[1])
            query = {k: v[0] for k, v in params.items() if k not in ("pin", "trust")}
            status, payload = _lazy('app_api', 'AppApi').dispatch("GET", parsed_path.split("/api2/", 1)[1], query, remote=True)
            return self._send_json(payload, status=status)

        if self.path.startswith(f'/{token}/exec'):
            sig = params.get('sig', [''])[0]
            if sig in state.APP_CONFIG.get("buttons", {}):
                action = state.APP_CONFIG["buttons"][sig].get("action")
                if action:
                    execute_macro(action)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
            return

        if self.path == f'/{token}/api/save' or self.path.startswith(f'/{token}/api/save?'):
            sig = params.get('sig', [''])[0]
            cat = params.get('cat', [''])[0]
            act = params.get('act', [''])[0]
            arg = params.get('arg', [''])[0]
            browser = params.get('browser', ['default'])[0]
            app_action = params.get('app_action', ['open'])[0]
            btn_text = params.get('btn_text', [''])[0]
            
            all_macros = get_all_macros()
            if cat in all_macros and act in all_macros[cat]:
                action_data = all_macros[cat][act].copy()
                if action_data.get("type") in ["custom_web", "custom_app", "custom_hotkey", "type_text"]:
                    action_data["custom_arg"] = arg
                if action_data.get("type") in ["custom_web", "web"]:
                    action_data["browser"] = browser
                if action_data.get("type") == "custom_app":
                    action_data["app_action"] = app_action
                
                if "buttons" not in state.APP_CONFIG:
                    state.APP_CONFIG["buttons"] = {}
                state.APP_CONFIG["buttons"][sig] = {"name": act, "action": action_data}
                if sig.startswith("NEX:P3_") or sig.startswith("NEX:P4_"):
                    state.APP_CONFIG["buttons"][sig]["btn_text"] = btn_text
                save_config(state.APP_CONFIG)
                if state.MAIN_WINDOW:
                    run_on_ui(lambda: state.MAIN_WINDOW.refresh_screen_buttons())
                    if sig.startswith("NEX:P3_") or sig.startswith("NEX:P4_"):
                        run_on_ui(lambda: state.MAIN_WINDOW.sync_nextion_texts())
                
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
            return
            
        if self.path.startswith(f'/{token}/api/save_page_name'):
            page = params.get('page', [''])[0]
            name = params.get('name', [''])[0]
            if "page_names" not in state.APP_CONFIG:
                state.APP_CONFIG["page_names"] = {}
            state.APP_CONFIG["page_names"][page] = name
            save_config(state.APP_CONFIG)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
            return

        if self.path.startswith(f'/{token}/api/save_accent'):
            color = params.get('color', [''])[0].strip()
            if re.match(r'^#[0-9A-Fa-f]{6}$', color):
                state.APP_CONFIG["accent_color"] = color.upper()
                save_config(state.APP_CONFIG)
                if state.MAIN_WINDOW:
                    try:
                        state.MAIN_WINDOW.config["accent_color"] = color.upper()
                        run_on_ui(state.MAIN_WINDOW.apply_theme)
                    except Exception:
                        pass
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
            return

        if self.path.startswith(f'/{token}/api/encoder'):
            mode = params.get('mode', [''])[0]
            if "encoder" not in state.APP_CONFIG:
                state.APP_CONFIG["encoder"] = {}
            if mode:
                state.APP_CONFIG["encoder"]["turn"] = mode
                save_config(state.APP_CONFIG)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
            return

        if self.path.startswith(f'/{token}/api/volume'):
            direction = params.get('dir', [''])[0]
            mode = params.get('mode', [state.APP_CONFIG.get("encoder", {}).get("turn", "general_volume")])[0]
            try:
                steps = int(params.get('steps', ['1'])[0])
            except:
                steps = 1
            steps = max(1, min(20, abs(steps)))
            delta = (0.01 * steps) if direction == "up" else (-0.01 * steps)
            try:
                if state.MAIN_WINDOW:
                    if mode in ["general_volume", "Genel Ses Seviyesi", "General Volume", ""]:
                        TASK_WORKER.submit(state.MAIN_WINDOW.change_master_volume, delta)
                    elif mode in ["brightness", "Ekran Parlaklığı", "Screen Brightness"]:
                        brightness_delta = max(-20, min(20, steps if direction == "up" else -steps))
                        execute_macro({"type": "nircmd", "cmd": f"changebrightness {brightness_delta}"})
                    else:
                        TASK_WORKER.submit(state.MAIN_WINDOW.change_app_volume, mode, delta)
            except Exception as e:
                if state.MAIN_WINDOW and hasattr(state.MAIN_WINDOW, "log_area"):
                    ui_log(f"Web volume error: {e}")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
            return

        if self.path.startswith(f'/{token}/api/audio_apps'):
            try:
                apps = state.MAIN_WINDOW.get_audio_mixer_apps() if state.MAIN_WINDOW else []
            except Exception:
                apps = []
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(apps, ensure_ascii=False).encode('utf-8'))
            return


        if not is_known_web_device_allowed(self._client_ip(), self._client_user_agent(), trusted_device_id):
            touch_web_device(raw_device, client_ip, client_ua, allowed_default=False)
            if new_session:
                end_web_sessions(raw_device)
            record_web_event("Tanınmayan cihaz engellendi", self._client_ip(), self._client_user_agent(), "Sadece tanınan cihazlar modu açık", "⛔")
            return self._send_plain_text("Bu cihaz tanınan cihazlar listesinde olmadığı için Web Kontrolü kullanılamaz.", status=403)

        self._log_web_login_once("Tanınan cihaz" if trusted_auth else "PIN girişi", trusted_device_id)
        # 2.5: Telefonda da yeni arayüz (NexStudio Web). Eski web arayüzü: adresin sonuna ?classic=1
        if params.get("classic", [""])[0] != "1" and os.path.exists(os.path.join(_lazy('app_api', 'WEB_UI_DIR'), "app.html")):
            if "pin" in params:
                # PIN adres çubuğunda kalmasın: oturum çerezi verildi, temiz adrese yönlendir
                return self._send_with_cookies(b"", "text/plain", extra_cookies, status=302, location=f"/{token}")
            html = _lazy('app_api', 'read_app_html')(f"/{token}/api2", True, "")
            return self._send_with_cookies(html.encode("utf-8"), "text/html; charset=utf-8", extra_cookies)
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        
        macros_json = json.dumps(get_all_macros(), ensure_ascii=False)
        buttons_json = json.dumps(get_physical_buttons(), ensure_ascii=False)
        translations_json = json.dumps(state.TRANSLATIONS, ensure_ascii=False)
        page_names_json = json.dumps(state.APP_CONFIG.get("page_names", {}), ensure_ascii=False)
        encoder_json = json.dumps(state.APP_CONFIG.get("encoder", {}), ensure_ascii=False)
        touch_map_json = json.dumps(TOUCH_UI_SLOT_TO_SIGNAL, ensure_ascii=False)
        device_connected_json = json.dumps(bool(state.MAIN_WINDOW and getattr(state.MAIN_WINDOW, "serial_thread", None) and state.MAIN_WINDOW.serial_thread.is_running))
        
        try:
            audio_apps_json = json.dumps(state.MAIN_WINDOW.get_audio_mixer_apps() if state.MAIN_WINDOW else [], ensure_ascii=False)
        except Exception:
            audio_apps_json = json.dumps([], ensure_ascii=False)
        
        user_agent = self.headers.get("User-Agent", "")
        is_mobile_client = bool(re.search(r"Android|iPhone|iPad|iPod|Mobile|Windows Phone", user_agent, re.I))
        logo_html = get_nexstudio_logo_html()
        known_for_page = state.APP_CONFIG.get("known_web_devices", {}) if isinstance(state.APP_CONFIG.get("known_web_devices", {}), dict) else {}
        trusted_name_for_page = known_for_page.get(trusted_device_id, {}).get("name", "") if trusted_device_id else ""
        trusted_json = json.dumps(bool(trusted_device_id))
        trusted_name_json = json.dumps(trusted_name_for_page, ensure_ascii=False)

        dashboard_html = f"""
        <!DOCTYPE html>
        <html lang="tr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>NexStudio Web</title>
            <style>
                :root {{
                    --bg-color: #070B14;
                    --bg-soft: #0B1220;
                    --surface: rgba(15, 23, 42, .78);
                    --surface-2: rgba(17, 24, 39, .86);
                    --border: rgba(148, 163, 184, .18);
                    --accent: {state.APP_CONFIG.get('accent_color', '#3B82F6')};
                    --text-main: #F8FAFC;
                    --text-muted: #94A3B8;
                    --success: #10B981;
                    --shadow: 0 24px 80px rgba(0,0,0,.38);
                }}
                * {{ box-sizing: border-box; -webkit-tap-highlight-color: transparent; }}
                html {{ scroll-behavior: smooth; }}
                body {{
                    background:
                        radial-gradient(circle at 16% 0%, rgba(59,130,246,.20), transparent 34%),
                        radial-gradient(circle at 90% 8%, rgba(139, 92, 246, .18), transparent 32%),
                        linear-gradient(145deg, #050814 0%, #0B1220 48%, #111827 100%);
                    color: var(--text-main);
                    font-family: Inter, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                    margin: 0;
                    padding: 18px 16px 104px;
                    min-height: 100vh;
                }}
                body::before {{
                    content: "";
                    position: fixed; inset: 0;
                    background-image: linear-gradient(rgba(255,255,255,.03) 1px, transparent 1px),
                                      linear-gradient(90deg, rgba(255,255,255,.03) 1px, transparent 1px);
                    background-size: 42px 42px;
                    mask-image: linear-gradient(to bottom, rgba(0,0,0,.7), transparent 75%);
                    pointer-events: none;
                }}
                .app-shell {{ position: relative; z-index: 1; max-width: 920px; margin: 0 auto; }}
                .header {{
                    display:flex; align-items:center; justify-content:space-between; gap: 14px;
                    margin: 4px auto 18px;
                }}
                .brandline {{ display:flex; align-items:center; gap: 13px; }}
                .brandmark {{
                    width: 48px; height: 48px; border-radius: 16px;
                    display:grid; place-items:center; background: rgba(255,255,255,.08); color:white;
                    border: 1px solid rgba(255,255,255,.14);
                    overflow: hidden;
                    font-weight: 950; font-size: 22px;
                    box-shadow: 0 16px 44px rgba(0,0,0,.28);
                }}
                .brandmark img {{ width:100%; height:100%; object-fit:cover; display:block; }}
                .brandmark span {{ display:grid; place-items:center; width:100%; height:100%; }}
                .header h1 {{ margin: 0; font-size: 27px; letter-spacing: -.04em; line-height:1; }}
                .header p {{ margin: 6px 0 0; color: var(--text-muted); font-size: 13px; }}
                .status-pill {{
                    border: 1px solid var(--border);
                    background: rgba(15, 23, 42, .62);
                    color: #C7D2FE;
                    padding: 9px 12px;
                    border-radius: 999px;
                    font-size: 12px;
                    font-weight: 850;
                    white-space: nowrap;
                }}
                .panel {{
                    background: var(--surface);
                    backdrop-filter: blur(22px);
                    -webkit-backdrop-filter: blur(22px);
                    border: 1px solid var(--border);
                    border-radius: 28px;
                    padding: 20px;
                    box-shadow: var(--shadow);
                    display: none;
                    animation: panelIn .26s ease both;
                    overflow: hidden;
                }}
                .panel.active {{ display: block; }}
                @keyframes panelIn {{ from {{ opacity: 0; transform: translateY(12px) scale(.99); }} to {{ opacity: 1; transform: translateY(0) scale(1); }} }}
                .section-title {{
                    display:flex; align-items:center; justify-content:space-between; gap: 12px;
                    padding-bottom: 14px; margin-bottom: 14px;
                    border-bottom: 1px solid var(--border);
                }}
                h3 {{ color: var(--text-main); margin: 0; font-size: 20px; letter-spacing: -.02em; }}
                .section-title small {{ color: var(--text-muted); font-size: 12px; font-weight: 700; }}
                label {{ display: block; margin: 14px 0 8px; font-weight: 800; color: #CBD5E1; font-size: 13px; }}
                .grid-list {{ display:grid; grid-template-columns: 1fr; gap: 10px; margin-bottom: 18px; }}
                @media (min-width: 720px) {{ .grid-list {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
                .btn-ctrl {{
                    position: relative;
                    background: linear-gradient(180deg, rgba(255,255,255,.055), rgba(255,255,255,.025));
                    border: 1px solid var(--border);
                    padding: 16px;
                    border-radius: 18px;
                    width: 100%;
                    color: var(--text-main);
                    font-size: 15px;
                    font-weight: 900;
                    text-align: left;
                    transition: transform .18s ease, border-color .18s ease, background .18s ease, box-shadow .18s ease;
                    cursor: pointer;
                    display: flex;
                    flex-direction: column;
                    gap: 7px;
                    overflow: hidden;
                }}
                .btn-ctrl::after {{
                    content: "";
                    position:absolute; right: 14px; top: 14px;
                    width: 9px; height: 9px; border-radius: 99px;
                    background: var(--accent);
                    box-shadow: 0 0 20px var(--accent);
                    opacity: .78;
                }}
                .btn-ctrl:hover, .btn-ctrl:focus {{
                    border-color: var(--accent);
                    background: rgba(59,130,246,.18);
                    transform: translateY(-2px);
                    box-shadow: 0 14px 36px rgba(0,0,0,.22);
                }}
                .btn-ctrl:active {{ transform: scale(.985); background: var(--accent); border-color: var(--accent); }}
                .btn-ctrl span {{ font-size: 12px; color: var(--text-muted); font-weight: 750; line-height: 1.35; padding-right: 20px; }}
                select, input {{
                    width: 100%;
                    padding: 15px 15px;
                    margin-bottom: 12px;
                    background: rgba(2, 6, 23, .48);
                    color: white;
                    border: 1px solid var(--border);
                    border-radius: 16px;
                    font-size: 15px;
                    outline: none;
                    transition: border-color .18s ease, box-shadow .18s ease, background .18s ease;
                }}
                select:focus, input:focus {{
                    border-color: var(--accent);
                    background: rgba(2, 6, 23, .72);
                    box-shadow: 0 0 0 4px rgba(59,130,246,.18);
                }}
                .btn-save {{
                    background: var(--accent); color: white; border: none;
                    padding: 17px; width: 100%; border-radius: 18px;
                    font-size: 16px; font-weight: 950; margin-top: 10px;
                    box-shadow: 0 16px 44px rgba(59,130,246,.28);
                    transition: transform .18s ease, filter .18s ease, box-shadow .18s ease;
                    cursor: pointer;
                }}
                .btn-save:hover {{ filter: brightness(1.06); transform: translateY(-1px); }}
                .btn-save:active {{ transform: scale(.98); }}
                #save-msg, #save-msg-pn {{
                    position: fixed;
                    left: 50%;
                    bottom: 92px;
                    transform: translateX(-50%);
                    background: rgba(2, 6, 23, .92);
                    border: 1px solid var(--success);
                    color: #D1FAE5 !important;
                    border-radius: 999px;
                    padding: 12px 18px;
                    min-width: 180px;
                    z-index: 220;
                    box-shadow: 0 18px 60px rgba(0,0,0,.36);
                }}
                .nav {{
                    position: fixed; bottom: 14px; left: 50%; transform: translateX(-50%);
                    width: min(560px, calc(100% - 24px));
                    background: rgba(15, 23, 42, .82); backdrop-filter: blur(22px);
                    -webkit-backdrop-filter: blur(22px);
                    border: 1px solid var(--border);
                    display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;
                    padding: 8px; z-index: 100;
                    border-radius: 24px;
                    box-shadow: 0 20px 70px rgba(0,0,0,.42);
                }}
                .nav button {{
                    background: transparent; color: var(--text-muted); border: none;
                    padding: 12px 8px; font-weight: 900; font-size: 13px;
                    border-radius: 17px; transition: all .2s ease;
                    display: flex; align-items: center; justify-content: center; gap: 7px;
                    cursor: pointer;
                }}
                .nav button.active {{ background: var(--accent); color: white; box-shadow: 0 10px 28px rgba(59,130,246,.24); }}

                /* Gelecekte arka plana görsel koymak için:
                   --bg-image: url('nexdeck-render.png');
                   body::after display:block yapılabilir. */
                :root {{
                    --bg-image: none;
                }}
                body::after {{
                    content: "";
                    position: fixed;
                    inset: 0;
                    background-image: var(--bg-image);
                    background-position: center;
                    background-size: cover;
                    opacity: .10;
                    filter: blur(18px);
                    transform: scale(1.04);
                    pointer-events: none;
                    z-index: 0;
                }}
                /* Mobil web için daha modern ve hafif görünüm */
                @media (max-width: 760px) {{
                    body {{
                        padding: 12px 10px 98px;
                        background:
                            radial-gradient(circle at 20% 0%, color-mix(in srgb, var(--accent) 24%, transparent), transparent 38%),
                            linear-gradient(155deg, #050814, #0B1220 52%, #111827);
                    }}
                    body::before,
                    body::after {{
                        display: none;
                    }}
                    .app-shell {{
                        max-width: 520px;
                    }}
                    .header {{
                        align-items: flex-start;
                        margin-bottom: 12px;
                    }}
                    .brandline {{
                        gap: 10px;
                    }}
                    .brandmark {{
                        width: 42px;
                        height: 42px;
                        border-radius: 15px;
                        font-size: 18px;
                    }}
                    .header h1 {{
                        font-size: 24px;
                    }}
                    .header p {{
                        font-size: 12px;
                    }}
                    .status-pill {{
                        padding: 8px 10px;
                        font-size: 11px;
                    }}
                    .panel {{
                        border-radius: 24px;
                        padding: 15px;
                        backdrop-filter: none;
                        -webkit-backdrop-filter: none;
                        box-shadow: 0 14px 38px rgba(0,0,0,.28);
                    }}
                    .section-title {{
                        display: block;
                        padding-bottom: 10px;
                        margin-bottom: 12px;
                    }}
                    h3 {{
                        font-size: 19px;
                    }}
                    .grid-list {{
                        grid-template-columns: 1fr !important;
                        gap: 9px;
                    }}
                    .btn-ctrl {{
                        min-height: 66px;
                        padding: 14px;
                        border-radius: 18px;
                        transition: none;
                    }}
                    .btn-ctrl:hover,
                    .btn-ctrl:focus {{
                        transform: none;
                        box-shadow: none;
                    }}
                    .touch-preview-card,
                    .touch-device,
                    .wheel-card,
                    .mixer-card {{
                        border-radius: 22px;
                        backdrop-filter: none;
                        -webkit-backdrop-filter: none;
                        box-shadow: none;
                    }}
                    .touch-grid {{
                        grid-template-columns: repeat(2, minmax(0, 1fr));
                        gap: 8px;
                    }}
                    .touch-btn {{
                        min-height: 72px;
                        border-radius: 16px;
                        padding: 10px;
                        transition: none;
                    }}
                    .touch-btn .top {{
                        font-size: 13px;
                    }}
                    .touch-btn .sub {{
                        font-size: 11px;
                    }}
                    .nav {{
                        bottom: 10px;
                        width: calc(100% - 18px);
                        border-radius: 22px;
                        padding: 7px;
                        backdrop-filter: none;
                        -webkit-backdrop-filter: none;
                    }}
                    .nav button {{
                        font-size: 12px;
                        padding: 11px 6px;
                    }}
                }}

                .accent-preview {{
                    border: 1px solid var(--border);
                    border-radius: 16px;
                    padding: 14px;
                    background: color-mix(in srgb, var(--accent) 14%, rgba(15,23,42,.72));
                    font-weight: 900;
                    color: white;
                    margin: 8px 0 12px;
                }}
                .accent-palette {{
                    display: grid;
                    grid-template-columns: repeat(6, 1fr);
                    gap: 9px;
                    margin: 10px 0 14px;
                }}
                .accent-chip {{
                    height: 38px;
                    border-radius: 14px;
                    border: 2px solid rgba(255,255,255,.16);
                    cursor: pointer;
                    box-shadow: inset 0 0 0 1px rgba(0,0,0,.18);
                }}
                .accent-chip.active {{
                    border-color: #FFFFFF;
                    box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent) 28%, transparent);
                }}
                .custom-accent-row {{
                    display: grid;
                    grid-template-columns: 1fr auto;
                    gap: 8px;
                    align-items: center;
                    margin-bottom: 12px;
                }}
                .custom-accent-row input {{
                    margin: 0;
                }}

                .touch-preview-card {{
                    margin-top: 14px;
                    border: 1px solid var(--border);
                    border-radius: 26px;
                    background:
                        linear-gradient(180deg, rgba(255,255,255,.07), rgba(255,255,255,.025)),
                        rgba(2, 6, 23, .34);
                    padding: 16px;
                    box-shadow: inset 0 0 0 1px rgba(255,255,255,.025), 0 18px 50px rgba(0,0,0,.24);
                }}
                .touch-device {{
                    border-radius: 24px;
                    border: 1px solid rgba(255,255,255,.14);
                    background:
                        radial-gradient(circle at 50% 0%, rgba(59,130,246,.16), transparent 42%),
                        linear-gradient(145deg, #020617, #0F172A);
                    padding: 16px;
                    position: relative;
                    overflow: hidden;
                }}
                .touch-device::before {{
                    content: "";
                    position: absolute;
                    left: 50%;
                    top: 8px;
                    transform: translateX(-50%);
                    width: 54px;
                    height: 4px;
                    border-radius: 999px;
                    background: rgba(148,163,184,.28);
                }}
                .touch-screen-head {{
                    display:flex;
                    align-items:center;
                    justify-content:space-between;
                    gap: 10px;
                    margin-bottom: 12px;
                    padding-top: 8px;
                }}
                .touch-screen-title {{
                    font-size: 13px;
                    color: #CBD5E1;
                    font-weight: 900;
                }}
                .touch-screen-page {{
                    font-size: 12px;
                    color: var(--text-muted);
                    border: 1px solid var(--border);
                    border-radius: 999px;
                    padding: 6px 10px;
                    background: rgba(15,23,42,.72);
                }}
                .touch-grid {{
                    display: grid;
                    grid-template-columns: repeat(4, minmax(0, 1fr));
                    gap: 10px;
                }}
                .touch-btn {{
                    min-height: 70px;
                    border: 1px solid rgba(148,163,184,.18);
                    border-radius: 18px;
                    background:
                        linear-gradient(180deg, rgba(255,255,255,.08), rgba(255,255,255,.025));
                    color: var(--text-main);
                    padding: 10px;
                    text-align: left;
                    cursor: pointer;
                    transition: transform .18s ease, border-color .18s ease, background .18s ease, box-shadow .18s ease;
                    display:flex;
                    flex-direction:column;
                    justify-content:space-between;
                    gap: 8px;
                }}
                .touch-btn:hover {{
                    transform: translateY(-2px);
                    border-color: var(--accent);
                    background: color-mix(in srgb, var(--accent) 16%, rgba(255,255,255,.045));
                    box-shadow: 0 12px 30px rgba(0,0,0,.24);
                }}
                .touch-btn:active {{
                    transform: scale(.98);
                    background: var(--accent);
                    border-color: var(--accent);
                }}
                .touch-btn .top {{
                    font-size: 13px;
                    font-weight: 950;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                }}
                .touch-btn .sub {{
                    font-size: 11px;
                    color: var(--text-muted);
                    line-height: 1.25;
                    overflow: hidden;
                    display: -webkit-box;
                    -webkit-line-clamp: 2;
                    -webkit-box-orient: vertical;
                }}
                .touch-btn:active .sub, .touch-btn:hover .sub {{
                    color: rgba(255,255,255,.86);
                }}
                .touch-btn.empty {{
                    opacity: .72;
                    border-style: dashed;
                }}
                .touch-btn.hidden-slot {{
                    visibility: hidden;
                    pointer-events: none;
                }}
                .mini-actions {{
                    display:flex;
                    gap: 10px;
                    flex-wrap: wrap;
                    margin: 10px 0 14px;
                }}
                .mini-chip {{
                    border: 1px solid var(--border);
                    background: rgba(15,23,42,.62);
                    color: #CBD5E1;
                    border-radius: 999px;
                    padding: 9px 11px;
                    font-size: 12px;
                    font-weight: 850;
                }}
                .assign-summary {{
                    border: 1px solid var(--border);
                    border-radius: 20px;
                    background: rgba(2,6,23,.34);
                    padding: 14px;
                    margin: 12px 0 16px;
                    color: var(--text-muted);
                    font-size: 13px;
                    line-height: 1.45;
                }}
                .assign-summary b {{
                    color: var(--text-main);
                }}


                .touch-toolbar {{
                    display:flex;
                    align-items:center;
                    justify-content:space-between;
                    gap: 10px;
                    margin: 10px 0 12px;
                }}
                .page-nav-btn {{
                    width: 48px;
                    height: 48px;
                    border-radius: 16px;
                    border: 1px solid var(--border);
                    background: rgba(15, 23, 42, .72);
                    color: white;
                    font-size: 20px;
                    font-weight: 950;
                    cursor: pointer;
                    transition: transform .18s ease, background .18s ease, border-color .18s ease;
                }}
                .page-nav-btn:hover {{
                    background: var(--accent);
                    border-color: var(--accent);
                    transform: translateY(-1px);
                }}
                .page-nav-btn:active {{ transform: scale(.96); }}
                .page-indicator {{
                    flex: 1;
                    text-align:center;
                    border: 1px solid var(--border);
                    border-radius: 16px;
                    padding: 13px 12px;
                    background: rgba(2,6,23,.36);
                    font-size: 13px;
                    font-weight: 900;
                    color: #CBD5E1;
                }}
                .wheel-card {{
                    margin-top: 18px;
                    border: 1px solid var(--border);
                    border-radius: 26px;
                    background:
                        radial-gradient(circle at 10% 0%, rgba(59,130,246,.16), transparent 36%),
                        rgba(2, 6, 23, .34);
                    padding: 16px;
                }}
                .wheel-layout {{
                    display:grid;
                    grid-template-columns: 120px 1fr;
                    gap: 16px;
                    align-items:center;
                }}
                @media (max-width: 520px) {{ .wheel-layout {{ grid-template-columns: 1fr; }} }}
                .wheel-visual {{
                    width: 110px;
                    height: 110px;
                    border-radius: 999px;
                    border: 1px solid rgba(59,130,246,.55);
                    background:
                        radial-gradient(circle at center, #111827 0 42%, transparent 43%),
                        conic-gradient(from 0deg, var(--accent), rgba(255,255,255,.16), var(--accent));
                    box-shadow: 0 20px 50px rgba(59,130,246,.18);
                    display:grid;
                    place-items:center;
                    font-size: 24px;
                    font-weight: 950;
                }}
                .wheel-actions {{
                    display:grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 10px;
                    margin-top: 10px;
                }}
                .wheel-btn {{
                    border: 1px solid var(--border);
                    background: rgba(15,23,42,.76);
                    color: white;
                    border-radius: 16px;
                    min-height: 48px;
                    font-size: 22px;
                    font-weight: 950;
                    cursor:pointer;
                    transition: all .18s ease;
                }}
                .wheel-btn:hover {{
                    background: var(--accent);
                    border-color: var(--accent);
                    transform: translateY(-1px);
                }}

                .wheel-visual {{
                    cursor: grab;
                    user-select: none;
                    touch-action: none;
                    transition: transform .08s linear, box-shadow .18s ease, border-color .18s ease;
                }}
                .wheel-visual:active {{
                    cursor: grabbing;
                    border-color: var(--accent);
                    box-shadow: 0 24px 70px rgba(59,130,246,.30);
                }}
                .wheel-visual.rotating {{
                    border-color: var(--accent);
                    box-shadow: 0 24px 70px rgba(59,130,246,.34);
                }}
                .mixer-note {{
                    margin-top: 9px;
                    color: var(--text-muted);
                    font-size: 12px;
                    line-height: 1.45;
                }}
                .mixer-row {{
                    display:grid;
                    grid-template-columns: 1fr auto;
                    gap: 10px;
                    align-items:end;
                }}
                .refresh-mixer-btn {{
                    border: 1px solid var(--border);
                    background: rgba(15,23,42,.76);
                    color: white;
                    border-radius: 16px;
                    height: 51px;
                    min-width: 54px;
                    font-size: 18px;
                    font-weight: 950;
                    cursor:pointer;
                    transition: all .18s ease;
                }}
                .refresh-mixer-btn:hover {{
                    background: var(--accent);
                    border-color: var(--accent);
                    transform: translateY(-1px);
                }}


                .footer {{ text-align: center; color: var(--text-muted); font-size: 12px; margin: 26px 0 0; }}
            </style>
        </head>
        <body>
        <main class="app-shell">
        <div class="header">
            <div class="brandline">
                <div class="brandmark">{logo_html}</div>
                <div>
                    <h1>NexStudio</h1>
                    <p>Web Kontrolü</p>
                </div>
            </div>
            <div class="status-pill">NexDeck Remote</div>
        </div>
        
        <div id="p-ctrl" class="panel active">
            <h3 id="lbl_ctrl_phys">Fiziksel Tuşlar</h3>
            <div id="ctrl-list-phys"></div>
            <div class="section-title" style="margin-top:18px;">
                <h3 id="lbl_ctrl_scr">Dokunmatik Ekran</h3>
                <small>Touch Preview</small>
            </div>
            <div class="touch-toolbar">
                <button class="page-nav-btn" onclick="changePreviewPage(-1)">‹</button>
                <div class="page-indicator" id="touch-page-label">Page</div>
                <button class="page-nav-btn" onclick="changePreviewPage(1)">›</button>
            </div>
            <select id="ctrl-page" onchange="renderControlList()" style="display:none;"></select>
            <div class="touch-preview-card">
                <div class="touch-device">
                    <div class="touch-screen-head">
                        <div class="touch-screen-title">NexDeck Touch Preview</div>
                        <div class="touch-screen-page" id="touch-page-mini-label">Page</div>
                    </div>
                    <div id="ctrl-list-scr" class="touch-grid"></div>
                </div>
            </div>
            <div class="wheel-card">
                <div class="section-title">
                    <h3>Tekerlek Kontrolü</h3>
                    <small>Encoder</small>
                </div>
                <div class="wheel-layout">
                    <div class="wheel-visual" id="web-wheel" title="Sürükleyerek çevir">◉</div>
                    <div>
                        <label>Tekerlek dönüş ataması</label>
                        <select id="encoder-mode" onchange="saveEncoderMode()">
                            <option value="general_volume">Genel Ses Seviyesi</option>
                            <option value="active_window">Aktif Pencere Sesi</option>
                            <option value="brightness">Ekran Parlaklığı</option>
                        </select>

                        <label>Ses karıştırıcısı</label>
                        <div class="mixer-row">
                            <select id="mixer-apps" onchange="selectMixerApp()"></select>
                            <button class="refresh-mixer-btn" onclick="refreshMixerApps()" title="Yenile">↻</button>
                        </div>
                        <div class="mixer-note">Uygulama seçersen tekerlek ve +/− tuşları o uygulamanın sesini kontrol eder.</div>

                        <div class="wheel-actions">
                            <button class="wheel-btn" onclick="webVolume('down')">−</button>
                            <button class="wheel-btn" onclick="webVolume('up')">+</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div id="p-assign" class="panel">
            <h3 id="lbl_assign_title">Tuş Özelleştir</h3>
            <label id="lbl_assign_type">Atama Türü:</label>
            <select id="assign-type" onchange="updateAssignUI()">
                <option value="phys" id="opt_phys">Fiziksel Tuşlar</option>
                <option value="screen" id="opt_scr">Dokunmatik Ekran</option>
            </select>
            <select id="assign-page" onchange="updateAssignUI()" style="display:none;"></select>
            
            <label id="lbl_which_key">Hangi Tuş?</label>
            <select id="sel-btn" onchange="loadCurrentAssign()"></select>
            
            <div id="div-screen-text" style="display:none;">
                <label id="lbl_screen_text">Ekranda Görünecek Yazı:</label>
                <input type="text" id="inp-screen-text" maxlength="15">
            </div>
            
            <label id="lbl_cat">Kategori:</label>
            <select id="sel-cat" onchange="updateActions()"></select>
            
            <label id="lbl_act">Görev:</label>
            <select id="sel-act" onchange="checkArg()"></select>
            
            <select id="sel-browser" style="display:none;">
                <option value="default" id="opt_b_def">Varsayılan Tarayıcı</option>
                <option value="chrome" id="opt_b_chr">Google Chrome</option>
                <option value="edge" id="opt_b_edg">Microsoft Edge</option>
                <option value="firefox" id="opt_b_fir">Mozilla Firefox</option>
            </select>
            
            <select id="sel-app-action" style="display:none;">
                <option value="open" id="opt_a_op">Uygulamayı Aç</option>
                <option value="close" id="opt_a_cl">Uygulamayı Kapat</option>
                <option value="force_close" id="opt_a_fc">Zorla Kapat (Görev Yöneticisi)</option>
            </select>
            
            <input type="text" id="inp-arg" placeholder="..." style="display:none;">
            
            <button class="btn-save" onclick="saveMacro()" id="btn_save">💾 Kaydet</button>
            <p id="save-msg" style="color:#10B981; display:none; text-align:center; font-weight:bold; margin-top:15px; font-size:18px;">Başarılı!</p>
        </div>
        
        <div id="p-settings" class="panel">
            <div class="section-title">
                <h3 id="lbl_set_title">Ayarlar</h3>
                <small>Preferences</small>
            </div>
            <label id="lbl_lang">Dil Seçimi:</label>
            <select id="sel-lang" onchange="changeLang()">
                <option value="tr">Türkçe</option>
                <option value="en">English</option>
            </select>

            <h3 style="margin-top:24px;">Bu Cihaz</h3>
            <div class="assign-summary" id="trust-status">Cihaz durumu kontrol ediliyor...</div>
            <input type="text" id="trust-device-name" placeholder="Örn: Ali Telefon, Eski Tablet, PCM">
            <button class="btn-save" onclick="trustThisDevice()" id="btn_trust_device">✅ Bu Cihazı Tanı</button>
            <p class="hint">Bu cihaz tanınırsa aynı tarayıcıdan sonraki girişlerde PIN istenmez. Tarayıcı verileri temizlenirse tekrar PIN gerekir.</p>
            
            <h3 style="margin-top:24px;">Web Genel Rengi</h3>
            <div class="accent-preview" id="accent-preview">NexStudio vurgu rengi</div>
            <div class="accent-palette" id="accent-palette"></div>
            <div class="custom-accent-row">
                <input type="text" id="web-accent-color" value="{state.APP_CONFIG.get('accent_color', '#3B82F6')}" placeholder="#3B82F6" maxlength="7">
                <button class="btn-save" style="margin-top:0;" onclick="applyCustomAccent()">Uygula</button>
            </div>
            <button class="btn-save" onclick="saveAccentColor()" id="btn_save_accent">🎨 Rengi Kaydet</button>
            <p id="save-msg-accent" style="color:#10B981; display:none; text-align:center; font-weight:bold; margin-top:15px; font-size:18px;">Başarılı!</p>

            <h3 id="lbl_page_names" style="margin-top:30px;">Sayfa İsimlerini Düzenle</h3>
            <label>Sayfa 1:</label><input type="text" id="pn-1">
            <label>Sayfa 2:</label><input type="text" id="pn-2">
            <label>Sayfa 3:</label><input type="text" id="pn-3">
            <label>Sayfa 4:</label><input type="text" id="pn-4">
            <button class="btn-save" onclick="savePageNames()" id="btn_save_pn">💾 Kaydet</button>
            <p id="save-msg-pn" style="color:#10B981; display:none; text-align:center; font-weight:bold; margin-top:15px; font-size:18px;">Başarılı!</p>
        </div>

        <div class="footer">
            &copy; 2026 NexHub / Ali Mert Taşcı. Tüm hakları saklıdır.
        </div>
        </main>

        <div class="nav">
            <button id="t-ctrl" class="active" onclick="switchTab('ctrl')"><span>⌁</span><span id="nav_ctrl">Kontrol</span></button>
            <button id="t-assign" onclick="switchTab('assign')"><span>✦</span><span id="nav_assign">Atama</span></button>
            <button id="t-settings" onclick="switchTab('settings')"><span>⚙</span><span id="nav_set">Ayarlar</span></button>
        </div>

        <script>
            const pin = "{correct_pin}";
            const token = "{token}";
            const isTrustedDevice = {trusted_json};
            const trustedDeviceName = {trusted_name_json};
            if (window.location.search.includes('pin=')) {{
                history.replaceState(null, '', '/' + token);
            }}
            function updateTrustStatus() {{
                const box = document.getElementById('trust-status');
                const btn = document.getElementById('btn_trust_device');
                if (!box || !btn) return;
                if (isTrustedDevice) {{
                    box.innerHTML = '✅ Bu cihaz tanınıyor' + (trustedDeviceName ? ': <b>' + trustedDeviceName + '</b>' : '') + '<br><span style="color:#94A3B8">Sonraki girişlerde PIN istenmez.</span>';
                    btn.innerText = '✅ Cihaz Zaten Tanınıyor';
                    btn.disabled = true;
                    btn.style.opacity = '.65';
                }} else {{
                    box.innerHTML = '⚠️ Bu cihaz henüz tanınmıyor.<br><span style="color:#94A3B8">İstersen bu tarayıcıya güven kaydı bırakabiliriz.</span>';
                    btn.innerText = '✅ Bu Cihazı Tanı';
                    btn.disabled = false;
                    btn.style.opacity = '1';
                }}
            }}
            async function trustThisDevice() {{
                const input = document.getElementById('trust-device-name');
                let name = (input && input.value.trim()) || '';
                if (!name) {{ name = prompt('Bu cihaz için bir ad gir:', 'Benim Cihazım') || ''; }}
                name = name.trim();
                if (!name) return;
                const res = await fetch(`/${{token}}/api/trust_device?pin=${{encodeURIComponent(pin)}}&name=${{encodeURIComponent(name)}}`);
                const data = await res.json().catch(() => ({{ok:false}}));
                if (data.ok) {{
                    try {{ localStorage.setItem('nexstudio_trust_token', data.trust_token || ''); }} catch(e) {{}}
                    alert('Cihaz tanındı. Sonraki girişlerde bu tarayıcıdan PIN istenmeyecek.');
                    location.href = '/' + token;
                }} else {{ alert(data.error || 'Cihaz tanınamadı.'); }}
            }}
            const macros = {macros_json};
            const physBtns = {buttons_json};
            const i18n = {translations_json};
            let pageNames = {page_names_json};
            let encoderConfig = {encoder_json};
            let audioApps = {audio_apps_json};
            let currentConfig = {json.dumps(state.APP_CONFIG.get("buttons", {}), ensure_ascii=False)};
            const touchMap = {touch_map_json};
            const deviceConnected = {device_connected_json};
            let currentLang = localStorage.getItem('nex_lang') || '{state.APP_CONFIG.get("language", "tr")}';
            
            function t(key) {{
                if (i18n[currentLang] && i18n[currentLang][key]) return i18n[currentLang][key];
                return i18n['tr'][key] || key;
            }}

            function getTouchSignal(page, slotIndex) {{
                const pageMap = touchMap[String(page)] || touchMap[page] || {{}};
                return pageMap[String(slotIndex)] || pageMap[slotIndex] || "";
            }}

            function getTouchVisualNo(page, slotIndex) {{
                const pageMap = touchMap[String(page)] || touchMap[page] || {{}};
                return Object.keys(pageMap)
                    .map(x => parseInt(x))
                    .filter(x => !Number.isNaN(x))
                    .sort((a,b) => a-b)
                    .filter(x => x <= slotIndex).length;
            }}
            
            function applyLang() {{
                document.getElementById('lbl_ctrl_phys').innerText = t('tab_physical');
                document.getElementById('lbl_ctrl_scr').innerText = t('tab_screen');
                document.getElementById('lbl_assign_title').innerText = t('web_tab_assign');
                document.getElementById('opt_phys').innerText = t('web_phys');
                document.getElementById('opt_scr').innerText = t('web_scr');
                document.getElementById('lbl_which_key').innerText = t('web_which_key');
                document.getElementById('lbl_cat').innerText = t('category');
                document.getElementById('lbl_act').innerText = t('task');
                document.getElementById('btn_save').innerText = t('web_save');
                document.getElementById('btn_save_pn').innerText = t('web_save');
                document.getElementById('save-msg').innerText = t('web_saved');
                document.getElementById('save-msg-pn').innerText = t('web_saved');
                document.getElementById('lbl_set_title').innerText = t('tab_settings');
                document.getElementById('lbl_lang').innerText = t('language');
                document.getElementById('nav_ctrl').innerText = t('web_tab_ctrl');
                document.getElementById('nav_assign').innerText = t('web_tab_assign');
                document.getElementById('nav_set').innerText = t('web_tab_set');
                document.getElementById('lbl_screen_text').innerText = t('screen_text');
                document.getElementById('lbl_page_names').innerText = t('web_page_names');
                
                document.getElementById('opt_b_def').innerText = t('browser_def');
                document.getElementById('opt_b_chr').innerText = t('browser_chr');
                document.getElementById('opt_b_edg').innerText = t('browser_edg');
                document.getElementById('opt_b_fir').innerText = t('browser_fir');
                
                document.getElementById('opt_a_op').innerText = t('app_open');
                document.getElementById('opt_a_cl').innerText = t('app_close');
                document.getElementById('opt_a_fc').innerText = t('app_force');
                
                document.getElementById('sel-lang').value = currentLang;
                
                document.getElementById('pn-1').value = pageNames['1'] || t('page_1');
                document.getElementById('pn-2').value = pageNames['2'] || t('page_2');
                document.getElementById('pn-3').value = pageNames['3'] || t('page_3');
                document.getElementById('pn-4').value = pageNames['4'] || t('page_4');
                
                let pages = [1, 2, 3, 4];
                let pHTML = "";
                pages.forEach(p => pHTML += `<option value="${{p}}">Sayfa ${{p}} (${{pageNames[p] || t('page_'+p)}})</option>`);
                document.getElementById('ctrl-page').innerHTML = pHTML;
                document.getElementById('assign-page').innerHTML = pHTML;
                
                renderControlList();
                updateAssignUI();
            }}
            
            function changeLang() {{
                currentLang = document.getElementById('sel-lang').value;
                localStorage.setItem('nex_lang', currentLang);
                applyLang();
            }}
            
            function switchTab(tab) {{
                document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
                document.querySelectorAll('.nav button').forEach(b => b.classList.remove('active'));
                document.getElementById('p-' + tab).classList.add('active');
                document.getElementById('t-' + tab).classList.add('active');
            }}
            
            function changePreviewPage(delta) {{
                let sel = document.getElementById('ctrl-page');
                let total = sel.options.length || 4;
                let idx = sel.selectedIndex;
                idx = (idx + delta + total) % total;
                sel.selectedIndex = idx;
                renderControlList();
            }}

            function cfgDetail(cfg) {{
                if (!cfg) return '';
                if (cfg.details) return cfg.details;
                const a = cfg.action || {{}};
                if (a.custom_arg) return a.custom_arg;
                if (a.cmd) return a.cmd;
                if (a.vk) return 'VK: ' + a.vk;
                return '';
            }}

            function saveEncoderMode() {{
                let mode = getCurrentEncoderMode();
                encoderConfig.turn = mode;
                fetch(`/${{token}}/api/encoder?mode=${{encodeURIComponent(mode)}}&pin=${{encodeURIComponent(pin)}}`).then(() => {{
                    showWebToast('Tekerlek ayarı kaydedildi');
                }});
            }}

            function webVolume(dir, steps=1) {{
                const mode = getCurrentEncoderMode();
                fetch(`/${{token}}/api/volume?dir=${{encodeURIComponent(dir)}}&steps=${{encodeURIComponent(steps)}}&mode=${{encodeURIComponent(mode)}}&pin=${{encodeURIComponent(pin)}}`).then(() => {{
                    showWebToast(dir === 'up' ? 'Ses artırıldı' : 'Ses azaltıldı');
                }});
            }}

            function showWebToast(message) {{
                let el = document.getElementById('save-msg');
                if (!el) return;
                el.innerText = message;
                el.style.display = "block";
                setTimeout(() => el.style.display = "none", 1400);
            }}
            
            let mixerRendering = false;

            function sanitizeMixerLabel(label) {{
                if (!label) return '';
                return String(label)
                    .replace(/\\.exe$/i, '')
                    .replace(/[_-]+/g, ' ')
                    .replace(/\\b\\w/g, c => c.toUpperCase());
            }}

            function isTechnicalMixerValue(value) {{
                value = String(value || '').toLowerCase();
                return value.includes('{') || value.includes('}') || value.includes('.dll') || value.includes('audiosrv') || value.includes('audioendpointbuilder');
            }}

            function renderMixerApps() {{
                let sel = document.getElementById('mixer-apps');
                if (!sel) return;
                mixerRendering = true;
                let current = encoderConfig.turn || 'general_volume';
                let html = `<option value="">Uygulama seçilmedi</option>`;

                if (audioApps && audioApps.length) {{
                    audioApps.forEach(item => {{
                        let label = sanitizeMixerLabel(item[0]);
                        let value = item[1];
                        if (isTechnicalMixerValue(label) || isTechnicalMixerValue(value)) return;
                        html += `<option value="${{value}}">${{label}}</option>`;
                    }});
                }} else {{
                    html += `<option value="__none__" disabled>Aktif ses uygulaması bulunamadı</option>`;
                }}

                sel.innerHTML = html;

                // Sadece görsel olarak mevcut ayarı seçili göster.
                // Bu satır hiçbir şekilde saveEncoderMode çağırmamalı.
                if (current && current.startsWith('app_volume:')) {{
                    let exists = Array.from(sel.options).some(opt => opt.value === current);
                    sel.value = exists ? current : "";
                }} else {{
                    sel.value = "";
                }}

                setTimeout(() => {{ mixerRendering = false; }}, 0);
            }}

            function selectMixerApp() {{
                if (mixerRendering) return;
                let sel = document.getElementById('mixer-apps');
                if (!sel || !sel.value || sel.value === '__none__') return;
                document.getElementById('encoder-mode').value = sel.value;
                saveEncoderMode();
            }}

            function refreshMixerApps() {{
                showWebToast('Ses karıştırıcısı yenileniyor...');
                fetch(`/${{token}}/api/audio_apps?pin=${{encodeURIComponent(pin)}}`)
                    .then(r => r.json())
                    .then(list => {{
                        audioApps = Array.isArray(list) ? list : [];
                        renderMixerApps();
                        showWebToast(audioApps.length ? `Ses karıştırıcısı yenilendi: ${{audioApps.length}} uygulama` : 'Aktif ses uygulaması bulunamadı');
                    }})
                    .catch(() => showWebToast('Ses karıştırıcısı alınamadı'));
            }}

            function getCurrentEncoderMode() {{
                let mixerSel = document.getElementById('mixer-apps');
                if (mixerSel && mixerSel.value && mixerSel.value !== '__none__') return mixerSel.value;
                let encSel = document.getElementById('encoder-mode');
                return encSel ? encSel.value : 'general_volume';
            }}

            let wheelDragging = false;
            let wheelLastAngle = 0;
            let wheelVisualAngle = 0;
            let wheelAccum = 0;

            function pointerAngle(evt, el) {{
                const rect = el.getBoundingClientRect();
                const cx = rect.left + rect.width / 2;
                const cy = rect.top + rect.height / 2;
                return Math.atan2(evt.clientY - cy, evt.clientX - cx) * 180 / Math.PI;
            }}

            function angleDiff(a, b) {{
                let d = a - b;
                while (d > 180) d -= 360;
                while (d < -180) d += 360;
                return d;
            }}

            function initWebWheel() {{
                const wheel = document.getElementById('web-wheel');
                if (!wheel) return;
                wheel.addEventListener('pointerdown', (evt) => {{
                    wheelDragging = true;
                    wheel.setPointerCapture(evt.pointerId);
                    wheel.classList.add('rotating');
                    wheelLastAngle = pointerAngle(evt, wheel);
                    evt.preventDefault();
                }});
                wheel.addEventListener('pointermove', (evt) => {{
                    if (!wheelDragging) return;
                    const a = pointerAngle(evt, wheel);
                    const d = angleDiff(a, wheelLastAngle);
                    wheelLastAngle = a;
                    wheelAccum += d;
                    wheelVisualAngle += d;
                    wheel.style.transform = `rotate(${{wheelVisualAngle}}deg)`;
                    const threshold = 14;
                    if (Math.abs(wheelAccum) >= threshold) {{
                        const steps = Math.max(1, Math.min(6, Math.floor(Math.abs(wheelAccum) / threshold)));
                        const dir = wheelAccum > 0 ? 'up' : 'down';
                        wheelAccum = 0;
                        webVolume(dir, steps);
                    }}
                    evt.preventDefault();
                }});
                function endDrag(evt) {{
                    if (!wheelDragging) return;
                    wheelDragging = false;
                    wheel.classList.remove('rotating');
                    try {{ wheel.releasePointerCapture(evt.pointerId); }} catch(e) {{}}
                }}
                wheel.addEventListener('pointerup', endDrag);
                wheel.addEventListener('pointercancel', endDrag);
                wheel.addEventListener('lostpointercapture', () => {{
                    wheelDragging = false;
                    wheel.classList.remove('rotating');
                }});
            }}
            
            function renderControlList() {{
                let htmlPhys = "";
                for (let sig in physBtns) {{
                    let cfg = currentConfig[sig] || {{}};
                    let name = cfg.name || t('empty');
                    let detail = cfgDetail(cfg);
                    htmlPhys += `<button class="btn-ctrl" onclick="fetch('/${{token}}/exec?sig=${{encodeURIComponent(sig)}}&pin=${{pin}}')"><b>${{physBtns[sig]}}</b><span>${{name}}${{detail ? ' • ' + detail : ''}}</span></button>`;
                }}
                document.getElementById('ctrl-list-phys').innerHTML = htmlPhys;
                
                let page = document.getElementById('ctrl-page').value;
                let htmlScr = "";
                document.getElementById('touch-page-label').innerText = `${{t('page_' + page) || 'Page ' + page}}`;
                for (let slot=0; slot<8; slot++) {{
                    let sig = getTouchSignal(page, slot);
                    if (!sig) {{
                        htmlScr += `<button class="touch-btn hidden-slot" tabindex="-1"></button>`;
                        continue;
                    }}
                    let cfg = currentConfig[sig] || {{}};
                    let name = cfg.name || t('empty');
                    let detail = cfgDetail(cfg);
                    let visualNo = getTouchVisualNo(page, slot);
                    let text = (page >= 3 && cfg.btn_text) ? cfg.btn_text : `Buton ${{visualNo}}`;
                    let emptyClass = cfg.name ? '' : ' empty';
                    htmlScr += `<button class="touch-btn${{emptyClass}}" onclick="fetch('/${{token}}/exec?sig=${{encodeURIComponent(sig)}}&pin=${{pin}}')"><span class="top">${{text}}</span><span class="sub">${{name}}${{detail ? ' • ' + detail : ''}}</span></button>`;
                }}
                document.getElementById('ctrl-list-scr').innerHTML = htmlScr;
            }}
            
            function updateAssignUI() {{
                let type = document.getElementById('assign-type').value;
                let pageSel = document.getElementById('assign-page');
                let btnSel = document.getElementById('sel-btn');
                let divText = document.getElementById('div-screen-text');
                
                btnSel.innerHTML = '';
                if (type === 'phys') {{
                    pageSel.style.display = 'none';
                    divText.style.display = 'none';
                    for (let sig in physBtns) {{
                        btnSel.innerHTML += `<option value="${{sig}}">${{physBtns[sig]}}</option>`;
                    }}
                }} else {{
                    pageSel.style.display = 'block';
                    let page = pageSel.value;
                    if (page >= 3) divText.style.display = 'block';
                    else divText.style.display = 'none';
                    
                    for (let slot=0; slot<8; slot++) {{
                        let sig = getTouchSignal(page, slot);
                        if (!sig) continue;
                        let visualNo = getTouchVisualNo(page, slot);
                        let name = currentConfig[sig] ? currentConfig[sig].name : t('empty');
                        btnSel.innerHTML += `<option value="${{sig}}">Buton ${{visualNo}} (${{name}})</option>`;
                    }}
                }}
                
                let selCat = document.getElementById('sel-cat');
                selCat.innerHTML = "";
                for (let cat in macros) {{
                    selCat.innerHTML += `<option value="${{cat}}">${{cat}}</option>`;
                }}
                updateActions();
                loadCurrentAssign();
            }}
            
            function updateActions() {{
                let cat = document.getElementById('sel-cat').value;
                let selAct = document.getElementById('sel-act');
                selAct.innerHTML = "";
                for (let act in macros[cat]) {{
                    selAct.innerHTML += `<option value="${{act}}">${{act}}</option>`;
                }}
                checkArg();
            }}
            
            function checkArg() {{
                let cat = document.getElementById('sel-cat').value;
                let act = document.getElementById('sel-act').value;
                let type = macros[cat][act].type;
                let inp = document.getElementById('inp-arg');
                let selBrowser = document.getElementById('sel-browser');
                let selApp = document.getElementById('sel-app-action');
                
                inp.style.display = "none";
                selBrowser.style.display = "none";
                selApp.style.display = "none";
                
                if (["custom_web", "custom_app", "custom_hotkey", "type_text"].includes(type)) {{
                    inp.style.display = "block";
                    if (type === "custom_web") {{ inp.placeholder = t('placeholder_web'); selBrowser.style.display = "block"; }}
                    else if (type === "custom_app") {{ inp.placeholder = t('placeholder_app'); selApp.style.display = "block"; }}
                    else if (type === "custom_hotkey") inp.placeholder = t('placeholder_shortcut');
                    else if (type === "type_text") inp.placeholder = t('placeholder_type_text');
                }} else if (type === "web") {{
                    selBrowser.style.display = "block";
                }}
            }}
            
            function loadCurrentAssign() {{
                let sig = document.getElementById('sel-btn').value;
                let cfg = currentConfig[sig];
                if (cfg) {{
                    if (cfg.btn_text) document.getElementById('inp-screen-text').value = cfg.btn_text;
                    else document.getElementById('inp-screen-text').value = "";
                    
                    if (cfg.action && cfg.action.custom_arg) document.getElementById('inp-arg').value = cfg.action.custom_arg;
                    else document.getElementById('inp-arg').value = "";
                    
                    if (cfg.action && cfg.action.browser) document.getElementById('sel-browser').value = cfg.action.browser;
                    if (cfg.action && cfg.action.app_action) document.getElementById('sel-app-action').value = cfg.action.app_action;
                }} else {{
                    document.getElementById('inp-screen-text').value = "";
                    document.getElementById('inp-arg').value = "";
                }}
            }}
            
            function saveMacro() {{
                let sig = document.getElementById('sel-btn').value;
                let cat = document.getElementById('sel-cat').value;
                let act = document.getElementById('sel-act').value;
                let arg = document.getElementById('inp-arg').value;
                let browser = document.getElementById('sel-browser').value;
                let app_action = document.getElementById('sel-app-action').value;
                let btn_text = document.getElementById('inp-screen-text').value;
                
                fetch(`/${{token}}/api/save?sig=${{encodeURIComponent(sig)}}&cat=${{encodeURIComponent(cat)}}&act=${{encodeURIComponent(act)}}&arg=${{encodeURIComponent(arg)}}&browser=${{encodeURIComponent(browser)}}&app_action=${{encodeURIComponent(app_action)}}&btn_text=${{encodeURIComponent(btn_text)}}&pin=${{pin}}`).then(() => {{
                    document.getElementById('save-msg').style.display = "block";
                    setTimeout(() => document.getElementById('save-msg').style.display = "none", 2000);
                    currentConfig[sig] = {{name: act, btn_text: btn_text}};
                    renderControlList();
                    updateAssignUI();
                    loadCurrentAssign();
                }});
            }}
            
            const accentPresets = ['#3B82F6', '#EF4444', '#10B981', '#8B5CF6', '#EC4899', '#F97316', '#22C55E', '#06B6D4', '#FACC15', '#64748B', '#FFFFFF', '#111827'];
            let selectedAccent = '{state.APP_CONFIG.get('accent_color', '#3B82F6')}';

            function normalizeAccent(color) {{
                color = (color || '').trim();
                if (!color.startsWith('#')) color = '#' + color;
                return /^#[0-9A-Fa-f]{{6}}$/.test(color) ? color.toUpperCase() : null;
            }}

            function setAccentColor(color) {{
                const normalized = normalizeAccent(color);
                if (!normalized) return;
                selectedAccent = normalized;
                document.getElementById('web-accent-color').value = normalized;
                document.documentElement.style.setProperty('--accent', normalized);
                document.querySelectorAll('.accent-chip').forEach(chip => {{
                    chip.classList.toggle('active', chip.dataset.color.toUpperCase() === normalized);
                }});
            }}

            function renderAccentPalette() {{
                const wrap = document.getElementById('accent-palette');
                if (!wrap) return;
                wrap.innerHTML = '';
                accentPresets.forEach(color => {{
                    const chip = document.createElement('button');
                    chip.type = 'button';
                    chip.className = 'accent-chip';
                    chip.dataset.color = color;
                    chip.style.background = color;
                    chip.onclick = () => setAccentColor(color);
                    wrap.appendChild(chip);
                }});
                setAccentColor(selectedAccent);
            }}

            function applyCustomAccent() {{
                const color = normalizeAccent(document.getElementById('web-accent-color').value);
                if (color) setAccentColor(color);
            }}

            function saveAccentColor() {{
                applyCustomAccent();
                fetch(`/${{token}}/api/save_accent?color=${{encodeURIComponent(selectedAccent)}}&pin=${{pin}}`).then(() => {{
                    document.getElementById('save-msg-accent').style.display = "block";
                    setTimeout(() => document.getElementById('save-msg-accent').style.display = "none", 2000);
                }});
            }}

            function savePageNames() {{
                let p1 = document.getElementById('pn-1').value;
                let p2 = document.getElementById('pn-2').value;
                let p3 = document.getElementById('pn-3').value;
                let p4 = document.getElementById('pn-4').value;
                
                fetch(`/${{token}}/api/save_page_name?page=1&name=${{p1}}&pin=${{pin}}`);
                fetch(`/${{token}}/api/save_page_name?page=2&name=${{p2}}&pin=${{pin}}`);
                fetch(`/${{token}}/api/save_page_name?page=3&name=${{p3}}&pin=${{pin}}`);
                fetch(`/${{token}}/api/save_page_name?page=4&name=${{p4}}&pin=${{pin}}`).then(() => {{
                    document.getElementById('save-msg-pn').style.display = "block";
                    setTimeout(() => document.getElementById('save-msg-pn').style.display = "none", 2000);
                    pageNames['1'] = p1; pageNames['2'] = p2; pageNames['3'] = p3; pageNames['4'] = p4;
                    applyLang();
                }});
            }}
            
            applyLang();
            renderAccentPalette();
            updateTrustStatus();
            initWebWheel();
            setTimeout(refreshMixerApps, 500);
        </script>
        </body></html>
        """
        if not is_mobile_client:
            desktop_html = f"""
            <!DOCTYPE html>
            <html lang="tr">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>NexStudio Desktop Web</title>
                <style>
                    :root {{
                        --bg: #080D18;
                        --panel: #101827;
                        --panel2: #152033;
                        --line: rgba(148,163,184,.18);
                        --text: #F8FAFC;
                        --muted: #94A3B8;
                        --accent: {state.APP_CONFIG.get('accent_color', '#3B82F6')};
                        --danger: #DC2626;
                        --ok: #10B981;
                    }}
                    * {{ box-sizing: border-box; }}
                    .brandmark img {{ width:100%; height:100%; object-fit:cover; display:block; }}
                    .brandmark span {{ display:grid; place-items:center; width:100%; height:100%; font-weight:950; }}
                    body {{
                        margin: 0;
                        min-height: 100vh;
                        background:
                            radial-gradient(circle at 0% 0%, rgba(59,130,246,.18), transparent 34%),
                            linear-gradient(135deg, #07101D, #111827 54%, #151B2D);
                        color: var(--text);
                        font-family: Inter, 'Segoe UI', Arial, sans-serif;
                        padding: 22px;
                    }}
                    .desktop-shell {{
                        width: min(1440px, 100%);
                        margin: 0 auto;
                    }}
                    .topbar {{
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        gap: 16px;
                        margin-bottom: 18px;
                    }}
                    .brand h1 {{
                        margin: 0;
                        font-size: 30px;
                        letter-spacing: -.04em;
                    }}
                    .brand p {{
                        margin: 6px 0 0;
                        color: var(--muted);
                        font-weight: 700;
                    }}
                    .pill {{
                        display: inline-flex;
                        align-items: center;
                        gap: 8px;
                        border: 1px solid var(--line);
                        background: rgba(15,23,42,.72);
                        color: #CBD5E1;
                        padding: 10px 14px;
                        border-radius: 999px;
                        font-size: 13px;
                        font-weight: 900;
                    }}
                    .tabs {{
                        position: sticky;
                        top: 12px;
                        z-index: 20;
                        display: flex;
                        gap: 10px;
                        background: rgba(8,13,24,.82);
                        border: 1px solid var(--line);
                        border-radius: 22px;
                        padding: 8px;
                        backdrop-filter: blur(10px);
                        margin-bottom: 18px;
                    }}
                    .tabs button {{
                        border: 0;
                        background: transparent;
                        color: var(--muted);
                        padding: 13px 18px;
                        border-radius: 16px;
                        font-weight: 950;
                        cursor: pointer;
                    }}
                    .tabs button.active {{
                        color: white;
                        background: var(--accent);
                    }}
                    .panel {{
                        display: none;
                    }}
                    .panel.active {{
                        display: block;
                    }}
                    .grid {{
                        display: grid;
                        grid-template-columns: repeat(12, 1fr);
                        gap: 16px;
                    }}
                    .card {{
                        background: linear-gradient(180deg, rgba(255,255,255,.045), rgba(255,255,255,.018)), var(--panel);
                        border: 1px solid var(--line);
                        border-radius: 22px;
                        padding: 18px;
                    }}
                    .card h2, .card h3 {{
                        margin: 0 0 12px;
                        letter-spacing: -.02em;
                    }}
                    .muted {{
                        color: var(--muted);
                        font-size: 13px;
                        font-weight: 700;
                    }}
                    .phys-card {{ grid-column: span 4; }}
                    .touch-card {{ grid-column: span 5; }}
                    .wheel-card {{ grid-column: span 3; }}
                    .wide {{ grid-column: span 12; }}
                    .button-grid {{
                        display: grid;
                        grid-template-columns: repeat(2, minmax(0, 1fr));
                        gap: 10px;
                    }}
                    .action-btn {{
                        border: 1px solid var(--line);
                        background: var(--panel2);
                        color: var(--text);
                        border-radius: 16px;
                        padding: 13px;
                        min-height: 66px;
                        text-align: left;
                        cursor: pointer;
                        font-weight: 950;
                    }}
                    .action-btn small {{
                        display: block;
                        color: var(--muted);
                        margin-top: 6px;
                        font-weight: 750;
                    }}
                    .action-btn:hover {{
                        border-color: var(--accent);
                    }}
                    .touch-toolbar {{
                        display: grid;
                        grid-template-columns: 48px 1fr 48px;
                        gap: 10px;
                        margin-bottom: 12px;
                    }}
                    .small-btn {{
                        border: 1px solid var(--line);
                        background: #0B1220;
                        color: white;
                        border-radius: 14px;
                        padding: 12px;
                        font-weight: 950;
                        cursor: pointer;
                    }}
                    .touch-grid {{
                        display: grid;
                        grid-template-columns: repeat(4, minmax(0, 1fr));
                        gap: 10px;
                        background: #07101D;
                        border: 1px solid var(--line);
                        border-radius: 20px;
                        padding: 14px;
                    }}
                    .touch-btn {{
                        min-height: 80px;
                        border-radius: 16px;
                        border: 1px solid var(--line);
                        background: var(--panel2);
                        color: white;
                        cursor: pointer;
                        text-align: left;
                        padding: 12px;
                        font-weight: 950;
                    }}
                    .touch-btn small {{
                        display:block;
                        color: var(--muted);
                        margin-top: 8px;
                    }}
                    .touch-btn.hidden {{
                        visibility: hidden;
                        pointer-events: none;
                    }}
                    select, input {{
                        width: 100%;
                        padding: 13px;
                        border-radius: 14px;
                        border: 1px solid var(--line);
                        background: #0B1220;
                        color: white;
                        margin: 7px 0 12px;
                        font-weight: 800;
                    }}
                    .save {{
                        width: 100%;
                        border: 0;
                        border-radius: 15px;
                        padding: 14px;
                        background: var(--accent);
                        color: white;
                        font-weight: 950;
                        cursor: pointer;
                    }}
                    .wheel {{
                        width: 96px;
                        height: 96px;
                        border-radius: 999px;
                        margin: 12px auto;
                        background: conic-gradient(from 0deg, var(--danger), #7C3AED, var(--accent), var(--danger));
                        display: grid;
                        place-items: center;
                        cursor: grab;
                        user-select: none;
                        touch-action: none;
                        position: relative;
                    }}
                    .wheel:active {{
                        cursor: grabbing;
                    }}
                    .wheel::before {{
                        content: "";
                        position: absolute;
                        top: 9px;
                        left: 50%;
                        width: 8px;
                        height: 18px;
                        border-radius: 999px;
                        background: white;
                        transform: translateX(-50%);
                        opacity: .9;
                    }}
                    .wheel::after {{
                        content: "";
                        width: 46px;
                        height: 46px;
                        background: #0B1220;
                        border-radius: 999px;
                        border: 1px solid var(--line);
                    }}
                    .vol-row {{
                        display: grid;
                        grid-template-columns: 1fr 1fr;
                        gap: 10px;
                    }}
                    .accent-preview {{
                        border: 1px solid var(--line);
                        border-radius: 16px;
                        padding: 14px;
                        background: color-mix(in srgb, var(--accent) 14%, #101827);
                        font-weight: 900;
                        margin-bottom: 12px;
                    }}
                    .accent-palette {{
                        display: grid;
                        grid-template-columns: repeat(8, 42px);
                        gap: 10px;
                        margin: 8px 0 14px;
                    }}
                    .accent-chip {{
                        width: 42px;
                        height: 42px;
                        border-radius: 14px;
                        border: 2px solid rgba(255,255,255,.16);
                        cursor: pointer;
                        box-shadow: inset 0 0 0 1px rgba(0,0,0,.2);
                    }}
                    .accent-chip.active {{
                        border-color: white;
                        box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent) 26%, transparent);
                    }}
                    .custom-accent-row {{
                        display: grid;
                        grid-template-columns: minmax(220px, 1fr) auto;
                        gap: 10px;
                        align-items: center;
                        margin-bottom: 14px;
                    }}
                    .custom-accent-row input {{
                        margin: 0;
                    }}

                    .toast {{
                        position: fixed;
                        right: 20px;
                        bottom: 20px;
                        background: #052E1A;
                        border: 1px solid #14532D;
                        color: #D1FAE5;
                        border-radius: 999px;
                        padding: 12px 16px;
                        display: none;
                        font-weight: 900;
                    }}
                    @media (max-width: 1100px) {{
                        .phys-card, .touch-card, .wheel-card {{ grid-column: span 12; }}
                    }}
                </style>
            </head>
            <body>
                <main class="desktop-shell">
                    <div class="topbar">
                        <div class="brand" style="display:flex;align-items:center;gap:14px;">
                            <div class="brandmark" style="width:48px;height:48px;border-radius:16px;overflow:hidden;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.14);display:grid;place-items:center;">{logo_html}</div>
                            <div>
                                <h1>NexStudio Web</h1>
                                <p>Masaüstü kontrol paneli</p>
                            </div>
                        </div>
                        <div class="pill">Güvenli bağlantı aktif</div>
                    </div>

                    <div class="tabs">
                        <button id="dt-control" class="active" onclick="showDesktopTab('control')">⌁ Kontrol</button>
                        <button id="dt-assign" onclick="showDesktopTab('assign')">✦ Atama Yap</button>
                        <button id="dt-settings" onclick="showDesktopTab('settings')">⚙ Ayarlar</button>
                    </div>

                    <section id="d-control" class="panel active">
                        <div class="grid">
                            <div class="card phys-card">
                                <h2>Fiziksel Tuşlar</h2>
                                <p class="muted">Kısa/uzun basım ve tekerlek butonu görevleri</p>
                                <div id="d-phys" class="button-grid"></div>
                            </div>

                            <div class="card touch-card">
                                <h2>Dokunmatik Ekran</h2>
                                <div class="touch-toolbar">
                                    <button class="small-btn" onclick="changePage(-1)">‹</button>
                                    <select id="d-page" onchange="renderDesktop()"></select>
                                    <button class="small-btn" onclick="changePage(1)">›</button>
                                </div>
                                <div id="d-touch" class="touch-grid"></div>
                            </div>

                            <div class="card wheel-card">
                                <h2>Tekerlek</h2>
                                <div class="wheel" id="d-wheel"></div>
                                <select id="d-encoder"></select>
                                <select id="d-mixer"></select>
                                <button class="small-btn" onclick="refreshMixerApps()">↻ Ses Uygulamaları</button>
                                <div class="vol-row">
                                    <button class="small-btn" onclick="webVolume('down', 2)">−</button>
                                    <button class="small-btn" onclick="webVolume('up', 2)">+</button>
                                </div>
                            </div>
                        </div>
                    </section>

                    <section id="d-assign" class="panel">
                        <div class="grid">
                            <div class="card wide">
                                <h2>Atama Yap</h2>
                                <label>Tür</label>
                                <select id="d-assign-type" onchange="updateDesktopAssignUI()">
                                    <option value="phys">Fiziksel Tuş</option>
                                    <option value="screen">Dokunmatik Ekran</option>
                                </select>
                                <label>Sayfa</label>
                                <select id="d-assign-page" onchange="updateDesktopAssignUI()"></select>
                                <label>Tuş</label>
                                <select id="d-sel-btn" onchange="loadDesktopAssign()"></select>
                                <label>Kategori</label>
                                <select id="d-sel-cat" onchange="updateDesktopActions()"></select>
                                <label>Görev</label>
                                <select id="d-sel-act" onchange="checkDesktopArg()"></select>
                                <input id="d-screen-text" placeholder="Ekran yazısı" style="display:none;">
                                <select id="d-browser" style="display:none;">
                                    <option value="default">Varsayılan tarayıcı</option>
                                    <option value="chrome">Google Chrome</option>
                                    <option value="edge">Microsoft Edge</option>
                                    <option value="firefox">Mozilla Firefox</option>
                                </select>
                                <select id="d-app-action" style="display:none;">
                                    <option value="open">Uygulamayı Aç</option>
                                    <option value="close">Uygulamayı Kapat</option>
                                    <option value="force_close">Zorla Kapat</option>
                                </select>
                                <input id="d-arg" placeholder="Ek bilgi" style="display:none;">
                                <button class="save" onclick="saveDesktopMacro()">💾 Kaydet</button>
                            </div>
                        </div>
                    </section>

                    <section id="d-settings" class="panel">
                        <div class="card wide">
                            <h2>Ayarlar</h2>
                            <p class="muted">Sayfa isimleri ve temel web ayarları</p>
                            <label>Bu Cihaz</label>
                            <div class="muted" id="d-trust-status" style="border:1px solid var(--line);border-radius:14px;padding:12px;background:rgba(2,6,23,.30);margin-bottom:12px;">Cihaz durumu kontrol ediliyor...</div>
                            <input id="d-trust-device-name" placeholder="Örn: Ali PC, Sunum Tableti">
                            <button class="save" onclick="desktopTrustThisDevice()">✅ Bu Cihazı Tanı</button>
                            <label>Web Genel Rengi</label>
                            <div class="accent-preview" id="d-accent-preview">NexStudio vurgu rengi</div>
                            <div class="accent-palette" id="d-accent-palette"></div>
                            <div class="custom-accent-row">
                                <input type="text" id="d-accent-color" value="{state.APP_CONFIG.get('accent_color', '#3B82F6')}" placeholder="#3B82F6" maxlength="7">
                                <button class="small-btn" onclick="applyDesktopCustomAccent()">Uygula</button>
                            </div>
                            <button class="save" onclick="saveDesktopAccent()">🎨 Rengi Kaydet</button>

                            <label>Sayfa 1</label><input id="d-pn-1">
                            <label>Sayfa 2</label><input id="d-pn-2">
                            <label>Sayfa 3</label><input id="d-pn-3">
                            <label>Sayfa 4</label><input id="d-pn-4">
                            <button class="save" onclick="saveDesktopPageNames()">💾 Sayfa İsimlerini Kaydet</button>
                        </div>
                    </section>
                </main>

                <div class="toast" id="d-toast">Kaydedildi</div>

                <script>
                    const pin = "{correct_pin}";
                    const token = "{token}";
                    const isTrustedDevice = {trusted_json};
                    const trustedDeviceName = {trusted_name_json};
                    if (window.location.search.includes('pin=')) {{ history.replaceState(null, '', '/' + token); }}
                    function updateDesktopTrustStatus() {{
                        const box = document.getElementById('d-trust-status');
                        if (!box) return;
                        if (isTrustedDevice) {{
                            box.innerHTML = '✅ Bu cihaz tanınıyor' + (trustedDeviceName ? ': <b>' + trustedDeviceName + '</b>' : '') + '<br>Sonraki girişlerde PIN istenmez.';
                        }} else {{
                            box.innerHTML = '⚠️ Bu cihaz henüz tanınmıyor.<br>İstersen bu tarayıcıya güven kaydı bırakabilirsin.';
                        }}
                    }}
                    async function desktopTrustThisDevice() {{
                        const input = document.getElementById('d-trust-device-name');
                        let name = (input && input.value.trim()) || '';
                        if (!name) name = prompt('Bu cihaz için bir ad gir:', 'Benim Cihazım') || '';
                        name = name.trim();
                        if (!name) return;
                        const res = await fetch(`/${{token}}/api/trust_device?pin=${{encodeURIComponent(pin)}}&name=${{encodeURIComponent(name)}}`);
                        const data = await res.json().catch(() => ({{ok:false}}));
                        if (data.ok) {{
                            try {{ localStorage.setItem('nexstudio_trust_token', data.trust_token || ''); }} catch(e) {{}}
                            alert('Cihaz tanındı. Sonraki girişlerde bu tarayıcıdan PIN istenmeyecek.');
                            location.href = '/' + token;
                        }} else {{ alert(data.error || 'Cihaz tanınamadı.'); }}
                    }}
                    const macros = {macros_json};
                    const physBtns = {buttons_json};
                    let pageNames = {page_names_json};
                    let encoderConfig = {encoder_json};
                    let audioApps = {audio_apps_json};
                    let currentConfig = {json.dumps(state.APP_CONFIG.get("buttons", {}), ensure_ascii=False)};
                    const touchMap = {touch_map_json};

                    function toast(msg='Kaydedildi') {{
                        const el = document.getElementById('d-toast');
                        el.innerText = msg;
                        el.style.display = 'block';
                        setTimeout(() => el.style.display = 'none', 1600);
                    }}
                    function showDesktopTab(tab) {{
                        ['control','assign','settings'].forEach(x => {{
                            document.getElementById('d-' + x).classList.toggle('active', x === tab);
                            document.getElementById('dt-' + x).classList.toggle('active', x === tab);
                        }});
                    }}
                    function getTouchSignal(page, slot) {{
                        const pm = touchMap[String(page)] || touchMap[page] || {{}};
                        return pm[String(slot)] || pm[slot] || "";
                    }}
                    function getTouchVisualNo(page, slot) {{
                        const pm = touchMap[String(page)] || touchMap[page] || {{}};
                        return Object.keys(pm).map(x => parseInt(x)).filter(x => !Number.isNaN(x)).sort((a,b)=>a-b).filter(x => x <= slot).length;
                    }}
                    function desktopCfgDetail(cfg) {{
                        if (!cfg) return '';
                        if (cfg.details) return cfg.details;
                        const a = cfg.action || {{}};
                        if (a.custom_arg) return a.custom_arg;
                        if (a.cmd) return a.cmd;
                        if (a.vk) return 'VK: ' + a.vk;
                        return '';
                    }}
                    function execSig(sig) {{
                        fetch(`/${{token}}/exec?sig=${{encodeURIComponent(sig)}}&pin=${{pin}}`).catch(()=>{{}});
                    }}
                    function renderDesktop() {{
                        const phys = document.getElementById('d-phys');
                        phys.innerHTML = '';
                        for (let sig in physBtns) {{
                            let cfg = currentConfig[sig] || {{}};
                            let detail = desktopCfgDetail(cfg);
                            phys.innerHTML += `<button class="action-btn" onclick="execSig('${{sig}}')">${{physBtns[sig]}}<small>${{cfg.name || 'Boş'}}${{detail ? ' • ' + detail : ''}}</small></button>`;
                        }}

                        const page = parseInt(document.getElementById('d-page').value || '1');
                        const touch = document.getElementById('d-touch');
                        touch.innerHTML = '';
                        for (let slot=0; slot<8; slot++) {{
                            const sig = getTouchSignal(page, slot);
                            if (!sig) {{
                                touch.innerHTML += `<button class="touch-btn hidden"></button>`;
                                continue;
                            }}
                            const cfg = currentConfig[sig] || {{}};
                            const detail = desktopCfgDetail(cfg);
                            const no = getTouchVisualNo(page, slot);
                            const title = (page >= 3 && cfg.btn_text) ? cfg.btn_text : `Buton ${{no}}`;
                            touch.innerHTML += `<button class="touch-btn" onclick="execSig('${{sig}}')">${{title}}<small>${{cfg.name || 'Boş'}}${{detail ? ' • ' + detail : ''}}</small></button>`;
                        }}
                    }}
                    function changePage(delta) {{
                        const el = document.getElementById('d-page');
                        let v = parseInt(el.value || '1') + delta;
                        v = Math.max(1, Math.min(4, v));
                        el.value = String(v);
                        renderDesktop();
                    }}
                    function initDesktop() {{
                        const dPage = document.getElementById('d-page');
                        const aPage = document.getElementById('d-assign-page');
                        for (let i=1;i<=4;i++) {{
                            const name = pageNames[String(i)] || `Sayfa ${{i}}`;
                            dPage.innerHTML += `<option value="${{i}}">${{name}}</option>`;
                            aPage.innerHTML += `<option value="${{i}}">${{name}}</option>`;
                            document.getElementById('d-pn-' + i).value = name;
                        }}
                        for (let cat in macros) document.getElementById('d-sel-cat').innerHTML += `<option value="${{cat}}">${{cat}}</option>`;
                        const enc = document.getElementById('d-encoder');
                        enc.innerHTML = `<option value="general_volume">Genel Ses Seviyesi</option><option value="brightness">Ekran Parlaklığı</option>`;
                        document.getElementById('d-mixer').innerHTML = `<option value="__none__">Uygulama seçilmedi</option>`;
                        updateDesktopAssignUI();
                        updateDesktopActions();
                        renderDesktop();
                        renderDesktopAccentPalette();
                        initDesktopWheel();
                        setTimeout(refreshMixerApps, 500);
                    }}
                    function updateDesktopAssignUI() {{
                        const type = document.getElementById('d-assign-type').value;
                        const pageSel = document.getElementById('d-assign-page');
                        const btnSel = document.getElementById('d-sel-btn');
                        const textInput = document.getElementById('d-screen-text');
                        btnSel.innerHTML = '';
                        if (type === 'phys') {{
                            pageSel.style.display = 'none';
                            textInput.style.display = 'none';
                            for (let sig in physBtns) btnSel.innerHTML += `<option value="${{sig}}">${{physBtns[sig]}}</option>`;
                        }} else {{
                            pageSel.style.display = 'block';
                            const page = parseInt(pageSel.value || '1');
                            textInput.style.display = page >= 3 ? 'block' : 'none';
                            for (let slot=0; slot<8; slot++) {{
                                const sig = getTouchSignal(page, slot);
                                if (!sig) continue;
                                const no = getTouchVisualNo(page, slot);
                                const cfg = currentConfig[sig] || {{}};
                                btnSel.innerHTML += `<option value="${{sig}}">Buton ${{no}} (${{cfg.name || 'Boş'}})</option>`;
                            }}
                        }}
                        loadDesktopAssign();
                    }}
                    function updateDesktopActions() {{
                        const cat = document.getElementById('d-sel-cat').value;
                        const act = document.getElementById('d-sel-act');
                        act.innerHTML = '';
                        for (let k in macros[cat]) act.innerHTML += `<option value="${{k}}">${{k}}</option>`;
                        checkDesktopArg();
                    }}
                    function checkDesktopArg() {{
                        const cat = document.getElementById('d-sel-cat').value;
                        const act = document.getElementById('d-sel-act').value;
                        const type = macros[cat][act].type;
                        document.getElementById('d-arg').style.display = ["custom_web","custom_app","custom_hotkey","type_text"].includes(type) ? 'block' : 'none';
                        document.getElementById('d-browser').style.display = ["custom_web","web"].includes(type) ? 'block' : 'none';
                        document.getElementById('d-app-action').style.display = type === 'custom_app' ? 'block' : 'none';
                    }}
                    function loadDesktopAssign() {{
                        const sig = document.getElementById('d-sel-btn').value;
                        const cfg = currentConfig[sig] || {{}};
                        document.getElementById('d-screen-text').value = cfg.btn_text || '';
                        document.getElementById('d-arg').value = cfg.action?.custom_arg || '';
                    }}
                    function saveDesktopMacro() {{
                        const sig = document.getElementById('d-sel-btn').value;
                        const cat = document.getElementById('d-sel-cat').value;
                        const act = document.getElementById('d-sel-act').value;
                        const arg = document.getElementById('d-arg').value;
                        const browser = document.getElementById('d-browser').value;
                        const app_action = document.getElementById('d-app-action').value;
                        const btn_text = document.getElementById('d-screen-text').value;
                        fetch(`/${{token}}/api/save?sig=${{encodeURIComponent(sig)}}&cat=${{encodeURIComponent(cat)}}&act=${{encodeURIComponent(act)}}&arg=${{encodeURIComponent(arg)}}&browser=${{encodeURIComponent(browser)}}&app_action=${{encodeURIComponent(app_action)}}&btn_text=${{encodeURIComponent(btn_text)}}&pin=${{pin}}`).then(() => {{
                            currentConfig[sig] = {{name: act, btn_text: btn_text}};
                            toast();
                            renderDesktop();
                            updateDesktopAssignUI();
                        }});
                    }}
                    const desktopAccentPresets = ['#3B82F6', '#EF4444', '#10B981', '#8B5CF6', '#EC4899', '#F97316', '#22C55E', '#06B6D4', '#FACC15', '#64748B', '#FFFFFF', '#111827'];
                    let desktopSelectedAccent = '{state.APP_CONFIG.get('accent_color', '#3B82F6')}';

                    function normalizeDesktopAccent(color) {{
                        color = (color || '').trim();
                        if (!color.startsWith('#')) color = '#' + color;
                        return /^#[0-9A-Fa-f]{{6}}$/.test(color) ? color.toUpperCase() : null;
                    }}

                    function setDesktopAccent(color) {{
                        const normalized = normalizeDesktopAccent(color);
                        if (!normalized) return;
                        desktopSelectedAccent = normalized;
                        document.getElementById('d-accent-color').value = normalized;
                        document.documentElement.style.setProperty('--accent', normalized);
                        document.querySelectorAll('#d-accent-palette .accent-chip').forEach(chip => {{
                            chip.classList.toggle('active', chip.dataset.color.toUpperCase() === normalized);
                        }});
                    }}

                    function renderDesktopAccentPalette() {{
                        const wrap = document.getElementById('d-accent-palette');
                        if (!wrap) return;
                        wrap.innerHTML = '';
                        desktopAccentPresets.forEach(color => {{
                            const chip = document.createElement('button');
                            chip.type = 'button';
                            chip.className = 'accent-chip';
                            chip.dataset.color = color;
                            chip.style.background = color;
                            chip.onclick = () => setDesktopAccent(color);
                            wrap.appendChild(chip);
                        }});
                        setDesktopAccent(desktopSelectedAccent);
                    }}

                    function applyDesktopCustomAccent() {{
                        const color = normalizeDesktopAccent(document.getElementById('d-accent-color').value);
                        if (color) setDesktopAccent(color);
                    }}

                    function saveDesktopAccent() {{
                        applyDesktopCustomAccent();
                        fetch(`/${{token}}/api/save_accent?color=${{encodeURIComponent(desktopSelectedAccent)}}&pin=${{pin}}`).then(() => toast('Renk kaydedildi'));
                    }}

                    function saveDesktopPageNames() {{
                        let jobs = [];
                        for (let i=1;i<=4;i++) {{
                            const name = document.getElementById('d-pn-' + i).value;
                            pageNames[String(i)] = name;
                            jobs.push(fetch(`/${{token}}/api/save_page_name?page=${{i}}&name=${{encodeURIComponent(name)}}&pin=${{pin}}`));
                        }}
                        Promise.all(jobs).then(() => {{ toast(); location.reload(); }});
                    }}
                    function getCurrentEncoderMode() {{
                        const mixer = document.getElementById('d-mixer').value;
                        if (mixer && mixer !== '__none__') return mixer;
                        return document.getElementById('d-encoder').value || 'general_volume';
                    }}

                    let desktopWheelSendTimer = null;
                    let desktopWheelQueued = 0;
                    function webVolume(dir, steps=1) {{
                        const sign = dir === 'up' ? 1 : -1;
                        desktopWheelQueued += sign * Math.max(1, steps || 1);
                        desktopWheelQueued = Math.max(-20, Math.min(20, desktopWheelQueued));

                        if (desktopWheelSendTimer) return;
                        desktopWheelSendTimer = setTimeout(() => {{
                            const amount = desktopWheelQueued;
                            desktopWheelQueued = 0;
                            desktopWheelSendTimer = null;
                            if (!amount) return;
                            const sendDir = amount > 0 ? 'up' : 'down';
                            const sendSteps = Math.min(20, Math.abs(amount));
                            fetch(`/${{token}}/api/volume?dir=${{sendDir}}&steps=${{sendSteps}}&mode=${{encodeURIComponent(getCurrentEncoderMode())}}&pin=${{pin}}`).catch(()=>{{}});
                        }}, 70);
                    }}

                    let desktopWheelDragging = false;
                    let desktopWheelLastAngle = 0;
                    let desktopWheelVisualAngle = 0;
                    let desktopWheelAccum = 0;

                    function desktopPointerAngle(evt, el) {{
                        const rect = el.getBoundingClientRect();
                        const cx = rect.left + rect.width / 2;
                        const cy = rect.top + rect.height / 2;
                        return Math.atan2(evt.clientY - cy, evt.clientX - cx) * 180 / Math.PI;
                    }}

                    function desktopAngleDiff(a, b) {{
                        let d = a - b;
                        while (d > 180) d -= 360;
                        while (d < -180) d += 360;
                        return d;
                    }}

                    function initDesktopWheel() {{
                        const wheel = document.getElementById('d-wheel');
                        if (!wheel) return;

                        wheel.addEventListener('pointerdown', (evt) => {{
                            desktopWheelDragging = true;
                            try {{ wheel.setPointerCapture(evt.pointerId); }} catch(e) {{}}
                            desktopWheelLastAngle = desktopPointerAngle(evt, wheel);
                            evt.preventDefault();
                        }});

                        wheel.addEventListener('pointermove', (evt) => {{
                            if (!desktopWheelDragging) return;
                            const a = desktopPointerAngle(evt, wheel);
                            const d = desktopAngleDiff(a, desktopWheelLastAngle);
                            desktopWheelLastAngle = a;
                            desktopWheelAccum += d;
                            desktopWheelVisualAngle += d;
                            wheel.style.transform = `rotate(${{desktopWheelVisualAngle}}deg)`;

                            const threshold = 14;
                            if (Math.abs(desktopWheelAccum) >= threshold) {{
                                const steps = Math.max(1, Math.min(8, Math.floor(Math.abs(desktopWheelAccum) / threshold)));
                                const dir = desktopWheelAccum > 0 ? 'up' : 'down';
                                desktopWheelAccum = 0;
                                webVolume(dir, steps);
                            }}
                            evt.preventDefault();
                        }});

                        function endDesktopWheel(evt) {{
                            if (!desktopWheelDragging) return;
                            desktopWheelDragging = false;
                            try {{ wheel.releasePointerCapture(evt.pointerId); }} catch(e) {{}}
                        }}

                        wheel.addEventListener('pointerup', endDesktopWheel);
                        wheel.addEventListener('pointercancel', endDesktopWheel);
                        wheel.addEventListener('lostpointercapture', () => {{
                            desktopWheelDragging = false;
                        }});
                    }}
                    function refreshMixerApps() {{
                        fetch(`/${{token}}/api/audio_apps?pin=${{pin}}`).then(r=>r.json()).then(apps => {{
                            audioApps = apps || [];
                            const sel = document.getElementById('d-mixer');
                            sel.innerHTML = `<option value="__none__">Uygulama seçilmedi</option>`;
                            audioApps.forEach(app => {{
                                const value = app.process || app.name || app;
                                const label = app.label || app.display || app.name || value;
                                sel.innerHTML += `<option value="${{value}}">${{label}}</option>`;
                            }});
                        }}).catch(()=>{{}});
                    }}
                    updateDesktopTrustStatus();
                    initDesktop();
                </script>
            </body>
            </html>
            """
            self.wfile.write(desktop_html.encode('utf-8'))
            return

        self.wfile.write(dashboard_html.encode('utf-8'))

class NexStudioHTTPServer(ThreadingHTTPServer):
    # 2.5.1: Windows'ta SO_REUSEADDR iki programın aynı portu dinlemesine izin veriyordu;
    # telefonun isteği yanlış NexStudio'ya gidip "Yetkisiz" dönüyordu. Port artık özel kullanımda.
    allow_reuse_address = False
    daemon_threads = True

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


class MobileServerThread(QThread):
    server_started = pyqtSignal(int)
    server_failed = pyqtSignal(str)
    server_stopped = pyqtSignal()

    def __init__(self, port=DEFAULT_MOBILE_PORT):
        super().__init__()
        self.port = port
        self.server = None
        self.is_running = False
        self.start_error = ""

    def run(self):
        try:
            self.server = NexStudioHTTPServer(('0.0.0.0', self.port), MobileHandler)
            self.is_running = True
            self.server_started.emit(self.port)
            self.server.serve_forever(poll_interval=0.2)
        except Exception as e:
            self.start_error = str(e)
            self.server_failed.emit(self.start_error)
            try:
                print(f"Mobile web server error on port {self.port}: {e}")
            except Exception:
                pass
        finally:
            self.is_running = False
            self.server_stopped.emit()

    def stop(self):
        try:
            if self.server:
                self.server.shutdown()
                self.server.server_close()
        except Exception:
            pass
        self.is_running = False

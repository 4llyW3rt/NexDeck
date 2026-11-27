# NexStudio — NEXSTUDIO ÖZGÜR YAZILIM LİSANSI (NPL-v2), Telif Hakkı (c) 2026 Ali Mert Taşcı / NexHub. Ayrıntılar: LICENSE.txt
"""
Otomatik güncelleme (2.6.4).

- Açılışta ve günde bir kez GitHub'daki en son NexStudio sürümüne bakar (anahtar/hesap gerekmez).
- Yeni sürüm varsa arayüze bildirir; kullanıcı "Güncelle" deyince:
    1) Kurulum dosyasını SADECE bu deponun resmi indirme adresinden indirir,
    2) yanındaki .sha256 dosyasıyla doğrular (tutmazsa dosyayı siler, kurmaz),
    3) NexStudio'yu kapatır, kurulumu sessizce çalıştırır ve yeni sürümü açar.
- Kurulum kullanıcı klasörüne yapıldığı için (2.6.4+) yönetici izni (UAC) istemez.
- Kaynaktan (python ile) çalışırken indirip doğrular ama kurmaz.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

from . import state
from .core import APP_VERSION, ui_log, write_error_log

REPO = "4llyW3rt/NexDeck"
LATEST_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
ALLOWED_PREFIX = f"https://github.com/{REPO}/releases/download/"
TAG_RE = re.compile(r"^nexstudio-v(\d+)\.(\d+)\.(\d+)$")
CHECK_INTERVAL = 24 * 3600

STATUS = {"state": "idle", "current": APP_VERSION, "latest": "", "notes": "", "page": "",
          "progress": 0, "error": "", "checked_at": 0}
_INFO = {}
_LOCK = threading.Lock()


def current_version():
    # NEXSTUDIO_FAKE_VERSION: sadece test için (güncelleme akışını denemek amacıyla eski sürüm gibi davran)
    return os.getenv("NEXSTUDIO_FAKE_VERSION") or APP_VERSION


def _ver(text):
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", text or "")
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)


def _http_json(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "NexStudio-Updater"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def _set(**kw):
    with _LOCK:
        STATUS.update(kw)


def status():
    with _LOCK:
        return dict(STATUS, current=current_version(), can_install=bool(getattr(sys, "frozen", False)))


def check(manual=False):
    """En son sürümü sorar. Yeni sürüm varsa STATUS.state = 'available'."""
    _set(state="checking", error="")
    try:
        rel = _http_json(LATEST_URL)
        m = TAG_RE.match(rel.get("tag_name", ""))
        if not m:
            raise ValueError("Beklenmeyen sürüm etiketi")
        latest = ".".join(m.groups())
        assets = {a["name"]: a["browser_download_url"] for a in rel.get("assets", [])}
        exe = next((n for n in assets if n.startswith("NexStudio_Setup_") and n.endswith(".exe")), "")
        sha = assets.get(exe + ".sha256", "")
        with _LOCK:
            _INFO.clear()
            _INFO.update(exe_name=exe, exe_url=assets.get(exe, ""), sha_url=sha, version=latest)
        newer = _ver(latest) > _ver(current_version())
        _set(state="available" if newer and exe and sha else "uptodate", latest=latest,
             notes=(rel.get("body") or "")[:4000], page=rel.get("html_url", ""), checked_at=time.time())
        if newer and (not exe or not sha):
            _set(state="uptodate", error="Yeni sürümün kurulum dosyası ya da doğrulama kodu bulunamadı.")
        return status()
    except Exception as e:
        _set(state="error", error=f"Güncelleme kontrol edilemedi: {e}", checked_at=time.time())
        if manual:
            write_error_log(f"Güncelleme kontrolü: {e}")
        return status()


def _download(url, dest):
    if not url.startswith(ALLOWED_PREFIX):
        raise ValueError("Güvenilmeyen indirme adresi")
    req = urllib.request.Request(url, headers={"User-Agent": "NexStudio-Updater"})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = r.read(256 * 1024)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if total:
                _set(progress=int(done * 100 / total))
    return dest


def download_and_verify():
    """Kurulum dosyasını indirir ve SHA-256 ile doğrular. Başarılıysa dosya yolunu döndürür."""
    with _LOCK:
        info = dict(_INFO)
    if not info.get("exe_url"):
        raise ValueError("Önce güncellemeyi kontrol edin")
    folder = os.path.join(tempfile.gettempdir(), "NexStudio_update")
    os.makedirs(folder, exist_ok=True)
    exe_path = os.path.join(folder, info["exe_name"])
    _set(state="downloading", progress=0, error="")
    try:
        sha_path = _download(info["sha_url"], exe_path + ".sha256")
        expected = open(sha_path, encoding="utf-8").read().split()[0].strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("Doğrulama kodu okunamadı")
        _download(info["exe_url"], exe_path)
        h = hashlib.sha256()
        with open(exe_path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        if h.hexdigest() != expected:
            os.remove(exe_path)
            raise ValueError("İndirilen dosya doğrulanamadı (SHA-256 tutmuyor); kurulmadı")
        _set(state="ready", progress=100)
        ui_log(f"⬇️ NexStudio {info['version']} indirildi ve doğrulandı")
        return exe_path
    except Exception as e:
        _set(state="error", error=str(e))
        write_error_log(f"Güncelleme indirme: {e}")
        raise


def install(exe_path, quit_app):
    """Kurulumu sessizce çalıştırır, bittiğinde yeni sürümü açar ve bu uygulamayı kapatır."""
    if not getattr(sys, "frozen", False):
        raise RuntimeError("Kaynaktan çalışırken otomatik kurulum yapılmaz")
    target = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "NexStudio", "NexStudio.exe")
    log = os.path.join(os.path.dirname(exe_path), "install.log")
    # Küçük bir yardımcı betik: NexStudio kapanana kadar bekler, kurar, yeni sürümü açar
    bat = os.path.join(os.path.dirname(exe_path), "guncelle.bat")
    with open(bat, "w", encoding="utf-8") as f:
        f.write("@echo off\r\nchcp 65001 >nul\r\n"
                f"timeout /t 2 /nobreak >nul\r\n"
                f'"{exe_path}" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /LOG="{log}"\r\n'
                f'if exist "{target}" start "" "{target}"\r\n')
    subprocess.Popen(["cmd", "/c", bat], creationflags=0x08000000 | 0x00000008)  # CREATE_NO_WINDOW | DETACHED_PROCESS
    _set(state="installing")
    ui_log("🔄 Güncelleme kuruluyor; NexStudio yeniden açılacak")
    quit_app()


def start_background_checks():
    """Açılıştan 15 sn sonra ve günde bir kez kontrol eder (Ayarlar'dan kapatılabilir)."""
    def loop():
        time.sleep(15)
        notified = ""
        while True:
            if state.APP_CONFIG.get("update_check", True):
                st = check()
                if st["state"] == "available" and st["latest"] != notified:
                    notified = st["latest"]
                    ui_log(f"🆕 NexStudio {st['latest']} yayınlandı (kurulu: {st['current']})")
                    win = state.MAIN_WINDOW
                    if win and getattr(win, "tray_icon", None):
                        from .core import run_on_ui, QSystemTrayIcon
                        run_on_ui(lambda: win.tray_icon.showMessage(
                            "NexStudio", f"Yeni sürüm hazır: {st['latest']}. Ayarlar'dan tek tıkla güncelleyebilirsin.",
                            QSystemTrayIcon.Information, 6000))
            time.sleep(CHECK_INTERVAL)

    threading.Thread(target=loop, name="NexUpdater", daemon=True).start()


# ---------------------------------------------------------------------------
# Eski (yönetici) kurulum: Program Files'ta kalan kopya
# ---------------------------------------------------------------------------
LEGACY_DIRS = [os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "NexStudio"),
               os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "NexStudio")]


def legacy_installs():
    """Şu an çalışan kopya dışında Program Files'ta kalan eski kurulumlar."""
    here = os.path.dirname(os.path.abspath(sys.executable)).lower()
    return [d for d in LEGACY_DIRS if os.path.isdir(d) and os.path.abspath(d).lower() != here]


def remove_legacy_installs():
    """Eski kurulumları kaldırır. Program Files yönetici izni ister: Windows bir kez UAC onayı sorar."""
    import ctypes
    started = 0
    for d in legacy_installs():
        unins = os.path.join(d, "unins000.exe")
        if os.path.exists(unins):
            exe, params = unins, "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART"
        else:  # kaldırıcısı olmayan artık klasör
            exe, params = "cmd.exe", f'/c rmdir /s /q "{d}"'
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 0)
        if rc > 32:
            started += 1
    return started

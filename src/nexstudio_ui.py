# =========================================================
# NEXSTUDIO ÖZGÜR YAZILIM LİSANSI (NPL-v2)
# Telif Hakkı (c) 2026 - Ali Mert Taşcı / NexHub
#
# Bu yazılım, topluluk odaklı gelişimi ve özgür kullanımı desteklemek amacıyla
# aşağıdaki şartlar altında sunulmuştur:
#
# 1. MÜLKİYET VE ATIF: Yazılımın orijinal yapımcısı Ali Mert TAŞCI'dır. NexHub, Ali Mert Taşcı tarafından geliştirilen proje/marka adıdır.
#    Yazılımın değiştirilmiş sürümlerinde veya eklentilerinde asıl yapımcıya
#    atıf yapılması zorunludur.
#
# 2. ANA KOD DEĞİŞİKLİĞİ: Kullanıcılar, yazılımdaki hataları gidermek,
#    performans artırmak veya yeni özellikler eklemek amacıyla ana kaynak
#    kodlarını değiştirme hakkına sahiptir.
#
# 3. ÜCRETSİZ KALMA ZORUNLULUĞU: Bu yazılım ve bu yazılımın kaynak kodu
#    kullanılarak geliştirilen tüm türev çalışmalar tamamen ücretsiz kalmak
#    zorundadır. Yazılımın kendisi veya değiştirilmiş bir hali asla parayla
#    satılamaz.
#
# 4. EKLENTİ (PLUGIN) SERBESTİSİ: NexStudio için eklenti veya modül
#    geliştirmek serbesttir. Eklenti geliştirenler, kendi yazdıkları ek
#    kodların haklarına sahiptir ancak NexStudio çekirdek yapısını ticari
#    amaçla kullanamazlar.
#
# 5. "OLDUĞU GİBİ" PRENSİBİ: Bu yazılım, geliştirme aşamasında hatalar
#    içerebilir. Yazılım olduğu gibi sunulur; kullanımından doğabilecek
#    donanımsal veya yazılımsal sorumluluk kullanıcıya aittir.
#
# 6. PAYLAŞIM ŞARTI: Eğer ana kodda bir değişiklik yapıp bunu yayınlıyorsanız,
#    yaptığınız değişiklikleri de aynı bu lisans şartlarıyla (ücretsiz ve
#    açık kaynak) paylaşmak zorundasınız.
# =========================================================

import sys
import os
import re
import json
import copy
import subprocess
import time
import winreg
import ctypes
import importlib.util
import glob
import webbrowser
import serial
import serial.tools.list_ports
import socket
import secrets
import string
import hashlib
import base64
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
import urllib.parse

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QTabWidget, QMessageBox, QTextEdit, 
    QListWidget, QListWidgetItem, QGroupBox, QColorDialog, QLineEdit,
    QSystemTrayIcon, QMenu, QAction, QScrollArea, QFrame, QSizePolicy, QFileDialog, QInputDialog, QSplitter, QDialog, QStackedWidget, QGraphicsOpacityEffect
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty, QRect, QPoint
from PyQt5.QtGui import QFont, QCursor, QColor, QIcon, QPixmap, QImage, QPainter, QPen, QPalette

# =========================================================
# 1. EKSTRA KÜTÜPHANE KONTROLLERİ
# =========================================================
try:
    import qrcode
    HAS_QR = True
except ImportError:
    HAS_QR = False

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    import comtypes # Ses kontrolü güvenlik izni için eklendi!
    HAS_PYCAW = True
except ImportError:
    HAS_PYCAW = False

try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False

# Global Ana Pencere Referansı
MAIN_WINDOW = None

# =========================================================
# 2. DOSYA YOLLARI VE KLASÖRLER
# =========================================================
def get_appdata_path():
    # NEXSTUDIO_DATA_DIR: test/geliştirme için ayrı veri klasörü (gerçek ayarlara dokunmadan dener).
    path = os.getenv("NEXSTUDIO_DATA_DIR") or os.path.join(os.getenv('APPDATA'), "NexStudio")
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

APP_DIR = get_appdata_path()
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
LOGS_DIR = os.path.join(APP_DIR, "logs")
PLUGINS_DIR = os.path.join(APP_DIR, "plugins")
LOCALES_DIR = os.path.join(APP_DIR, "locales")
NIRCMD_PATH = get_resource_path("nircmd.exe")
APP_ICON_PATH = get_resource_path("app_icon.ico")
NEXSTUDIO_LOGO_CANDIDATES = ["Logo.png", "logo.png", "nexstudio_logo.png", "app_logo.png", "Logo(1).png"]

def find_nexstudio_logo_path():
    """Web arayüzü için logo dosyasını birkaç olası isimden güvenli şekilde bulur."""
    for logo_name in NEXSTUDIO_LOGO_CANDIDATES:
        try:
            logo_path = get_resource_path(logo_name)
            if os.path.exists(logo_path):
                return logo_path
        except Exception:
            pass
    return ""

def get_nexstudio_logo_data_uri():
    """Logoyu web HTML içine gömülebilecek data URI olarak döndürür; paketlemede dosya yolu kaybolsa bile çalışır."""
    try:
        logo_path = find_nexstudio_logo_path()
        if not logo_path:
            return ""
        ext = os.path.splitext(logo_path)[1].lower().replace(".", "") or "png"
        if ext == "jpg":
            ext = "jpeg"
        with open(logo_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")
        return f"data:image/{ext};base64,{encoded}"
    except Exception:
        return ""

def get_nexstudio_logo_html():
    """Web arayüzlerinde logo bulunursa görseli, bulunamazsa sade N işaretini döndürür."""
    src = get_nexstudio_logo_data_uri()
    if src:
        return f'<img src="{src}" alt="NexStudio">'
    return '<span>N</span>'

NEXSTUDIO_LOGO_PATH = find_nexstudio_logo_path()
NEXHUB_YOUTUBE_CHANNEL = "https://www.youtube.com/@NexHubCo"

# Gizli sahiplik işaretleri / telif doğrulama notları
NEXSTUDIO_LICENSE_NAME = "NEXSTUDIO ÖZGÜR YAZILIM LİSANSI (NPL-v2)"
NEXSTUDIO_COPYRIGHT = "Telif Hakkı (c) 2026 - Ali Mert Taşcı / NexHub"
NEXSTUDIO_OWNER_SIGNATURE = "Ali Mert Taşcı|NexHub|NexStudio"
NEXSTUDIO_PROVENANCE_MARKERS = [
    "NPL-v2:AMT:CORE",
    "NEXSTUDIO:AUTHOR:ALI_MERT_TASCI",
    "NEXHUB:OWNER:ALI_MERT_TASCI",
    "NEXHUB:PROJECT_BRAND",
    "NEXSTUDIO:COMMUNITY_FREE_ONLY",
]
NEXSTUDIO_BUILD_CHANNEL = "Public 2.5"
NEXSTUDIO_BUILD_ID = "NEX-25-AMT"
# Zero-width provenance watermark; kişisel e-posta/handle içermez, çalışma akışını etkilemez.
NEXSTUDIO_ZERO_WIDTH_WATERMARK = "​‌​‌‍​​‌‌‍‌​‌​‍​‌‌​‍‌‌​​"

# =========================================================
# GÜNCELLEME REHBERİ / CHANGELOG
# Burayı düzenleyerek başlangıç ekranındaki "Güncelleme Rehberi" kartını
# kolayca değiştirebilirsin. Dil aktif dile göre otomatik seçilir.
# Format (2.0): sürüm grupları, en yeni üstte:
#   ("Sürüm", "Tarih", ["Madde 1", "Madde 2", ...])
# Eski sürümleri silme; kart kaydırılabilir, tüm geçmiş görünür.
# =========================================================
NEXSTUDIO_CHANGELOG = {
    "tr": [
        ("2.5", "27.11.2026", [
            "Yeni arayüz: cihaz ortada; görevler tuşlara sürükle-bırak ile ya da tıklayarak atanıyor.",
            "Her tuşa emoji ya da kendi resmini koyabilirsin; uzun basış ayrı sekmede.",
            "Açık/koyu tema, vurgu rengi, arka plan rengi veya fotoğrafı ve panel şeffaflığı.",
            "NexStudio Web: telefondan aynı arayüz. 'Kontrol' modunda tuşa dokununca görev bilgisayarda çalışır; 'Düzenle' modunda atama yapılır.",
            "Telefon sayfasında gerçek QR kod, PIN, tanınan cihazlar.",
            "Eski görünüm duruyor: Ayarlar > Gelişmiş > Klasik görünüm. Klasikten geri dönmek için Ayarlar > 'Yeni görünüme geç'.",
            "NexStudio ikinci kez açılınca uyarı yerine mevcut pencere öne gelir.",
            "Tekerlek yeniden dönüyor: sürükleyerek, fare tekerleğiyle ya da ok tuşlarıyla çevir; telefonda da çalışır.",
            "Canlı gösterim: cihazdaki tuşa basınca ekranda yanıp söner, tekerleği çevirince ekrandaki tekerlek döner.",
        ]),
        ("2.0", "25–27.11.2026", [
            "Kararlılık sürümü: çökme, donma ve tuşların ardarda çalışması sorunlarının kökleri giderildi.",
            "Tuşlar SendInput + gerçek tarama kodu ile ve kısa basılı tutularak gönderiliyor; OBS kısayolları ve oyunlar tuşu kaçırmıyor.",
            "Firmware 2.0: NexDeck tuşları gerçek USB klavye gibi basabiliyor (hile korumalı oyunlar için). Ayarlar > Tuş Gönderimi.",
            "Görevler ayrı kuyrukta çalışıyor; arayüz donmuyor, gecikmiş görevler topluca tetiklenmiyor. Eklentiler kendi thread'inde çalışıyor.",
            "Cihaz kablosu çıkınca bildirim gösteriliyor ve takılınca otomatik yeniden bağlanıyor; COM numarası değişse de cihaz bulunuyor.",
            "Birden fazla NexDeck listeleniyor ve adlandırılabiliyor.",
            "Profil görevleri: cihazdaki bir tuşa 'Sonraki/Önceki profil' veya belirli profile geçiş atanabiliyor.",
            "Ayarlar atomik kaydediliyor ve yedekleniyor; bozulursa yedekten dönülüyor. Not Defteri ile kaydedilmiş ayar dosyası da okunuyor.",
            "Web Kontrolü arayüzü başka thread'den değiştirmiyor (rastgele çökmeler giderildi); yanlış PIN günlüğe düz metin yazılmıyor.",
            "Aynı anda iki NexStudio açılması engellendi; hatalar logs/error.log dosyasına kaydediliyor.",
            "Güncelleme Rehberi artık tüm eski sürümleri gösteriyor ve kaydırılabiliyor.",
        ]),
        ("1.5 Final", "18.06.2026", [
            "Web Kontrolü, cihaz güvenliği, günlük yönetimi ve paketleme yayın adayı seviyesine getirildi.",
            "Web Kontrolü sayfası sadeleştirildi; PIN, bağlantı ve QR gibi gizli bilgiler ayrı güvenli panelde yönetiliyor.",
            "QR büyütme, bağlantı kopyalama, PIN yenileme ve QR/link yenileme araçları daha anlaşılır hale getirildi.",
            "Tanınan cihaz sistemi: kullanıcı onayıyla kaydedilen cihazlar aynı tarayıcıdan PIN girmeden bağlanabilir.",
            "Hatalı PIN ekranı yenilendi; 5 hatalı denemeden sonra geri sayımlı geçici kilitleme.",
            "Başarılı girişler, hatalı PIN denemeleri ve yetkisiz web istekleri sistem günlüğüne ve web geçmişine kaydediliyor.",
            "Sistem günlüğü gizlenebilir; temizleme, TXT dışa aktarma ve 7 günden eski kayıtları otomatik silme.",
            "Web Kontrolü ve Ayarlar ekranları ayrıştırıldı; son bağlantı, tanınan cihazlar, IP gizleme ve sadece tanınan cihazlara izin seçenekleri.",
            "Uygulama/tray simgesi, arka plandan geri açılış, tam ekran arka planı ve paketleme iyileştirildi.",
        ]),
        ("1.5.8 – 1.5.10", "18.06.2026", [
            "PIN/URL/QR varsayılan olarak gizleniyor; göster/gizle paneli ve QR büyütme penceresi eklendi.",
            "Logo web sayfasına gömülü olarak ekleniyor; paketlemede kaybolmuyor.",
            "Son bağlantı / son cihaz kartı eklendi, son cihazı adlandırma daha görünür hale geldi.",
            "Web oturumlarını sıfırlama artık QR/link ve PIN'i de yeniliyor.",
            "Web Kontrolü kartı tam genişlik düzenine alındı; Ayarlar'a son bağlantı özeti eklendi.",
        ]),
        ("1.5.6 – 1.5.7", "17.06.2026", [
            "Sistem günlüğü temizleme, TXT dışa aktarma ve günlük dosyası tutma eklendi.",
            "5 hatalı PIN'den sonra 5 dakikalık geçici engel; tanınan cihazlar, cihaza isim verme ve cihaz unutma.",
            "PIN yenileme, web oturumlarını sıfırlama, otomatik web başlatma, IP gizleme ve sadece tanınan cihazlar seçenekleri.",
            "Web PIN ekranına logo; hatalı PIN mesajı kart içinde, kilitlenince canlı geri sayım.",
            "Web durumu kartı: port, PIN, son giriş, tanınan cihaz sayısı ve bağlantı adresi.",
        ]),
        ("1.5.3 – 1.5.5", "17.06.2026", [
            "Tam ekran / büyütmede görünen beyaz alan sorunu giderildi.",
            "Tray'den geri açılınca uygulama normal boyutta açılıyor.",
            "Web portu doluysa otomatik başka port deneniyor ve günlüğe yazılıyor.",
            "Başarılı web girişleri cihaz türü, işletim sistemi ve tarayıcı bilgisiyle günlüğe yazılıyor.",
            "Sistem Günlüğü sol menüde gizlenip Ayarlar'dan açılabiliyor.",
        ]),
        ("1.0", "06.06.2026", [
            "Arayüz düzeni sadeleştirildi; ikonlar, başlıklar ve gezinme yapısı daha okunaklı hale getirildi.",
            "Ses kontrolü %1 adımlı hale getirildi ve Windows ses karıştırıcısı ile daha uyumlu çalışacak şekilde düzenlendi.",
            "Tekerlek ayarı yalnızca Tekerlek Butonu panelinden yönetilecek şekilde düzenlendi.",
            "Web Kontrolü ve Hesap özellikleri ayrıştırıldı; geliştirme aşamasındaki bölümler kullanıcıya açıkça belirtildi.",
        ]),
    ],
    "en": [
        ("2.5", "2026-11-27", [
            "New UI: the device is in the middle; drag actions onto keys or click to assign.",
            "Emoji or your own image per key; long press in its own tab.",
            "Light/dark theme, accent color, background color or photo, panel transparency.",
            "NexStudio Web: the same UI on your phone, with Control and Edit modes.",
            "Real QR code, PIN and trusted devices on the Phone page.",
            "Classic view is still available from Settings > Advanced.",
        ]),
        ("2.0", "2026-11-25/27", [
            "Stability release: root causes of crashes, freezes and repeated key triggers were fixed.",
            "Keys are sent with SendInput using real scan codes and a short hold; OBS hotkeys and games no longer miss them.",
            "Firmware 2.0: NexDeck can press keys as a real USB keyboard (for anti-cheat protected games). Settings > Key Sending.",
            "Tasks run in a separate queue; the UI no longer freezes and stale tasks are not fired in bursts. Plugins run in their own thread.",
            "Unplugging the device shows a notification and it reconnects automatically, even if its COM number changes.",
            "Multiple NexDecks are listed and can be renamed.",
            "Profile actions: assign Next/Previous profile or a specific profile to any device button.",
            "Settings are saved atomically with a backup; files saved by Notepad are read correctly.",
            "Web Control no longer touches the UI from background threads; wrong PINs are not logged in plain text.",
            "Only one NexStudio instance can run; errors are written to logs/error.log.",
            "The changelog now shows every past release and can be scrolled.",
        ]),
        ("1.5 Final", "2026-06-18", [
            "Web Control, device security, log management and packaging brought to release quality.",
            "PIN, link and QR details are managed in a separate secure panel.",
            "Trusted devices can reconnect from the same browser without a PIN.",
            "Timed lockout after 5 wrong PINs; logins and unauthorized requests are logged.",
            "System log can be hidden, cleared, exported; logs older than 7 days are deleted automatically.",
        ]),
        ("1.5.3 – 1.5.10", "2026-06-17/18", [
            "Hidden-by-default PIN/URL/QR, QR enlarge window, embedded logo, last-connection card.",
            "Log export, trusted devices, PIN refresh, session reset, IP masking options.",
            "Fullscreen white-area fix, tray restore size, automatic free web port.",
        ]),
        ("1.0", "2026-06-06", [
            "Cleaner layout, icons and navigation.",
            "1% volume steps that work better with the Windows mixer.",
            "Wheel settings managed only from the Wheel Button panel.",
            "Web Control and Account features separated.",
        ]),
    ],
}

if not os.path.exists(PLUGINS_DIR): os.makedirs(PLUGINS_DIR)
if not os.path.exists(LOCALES_DIR): os.makedirs(LOCALES_DIR)
if not os.path.exists(LOGS_DIR): os.makedirs(LOGS_DIR)

# =========================================================
# 2.5 ÇEKİRDEK ALTYAPI (2.0)
# - Thread-güvenli log: arka thread'ler Qt widget'ına doğrudan dokunmaz.
# - Makro kuyruğu: görevler arayüzü dondurmadan, sırayla ve ayrı thread'de çalışır.
# - Hata günlüğü: exe'de konsol olmadığı için hatalar logs/error.log dosyasına yazılır.
# =========================================================
import threading
import queue
import traceback
import shutil
from PyQt5.QtCore import QObject

APP_VERSION = "2.5.0"
ERROR_LOG_FILE = os.path.join(LOGS_DIR, "error.log")
CONFIG_BACKUP_FILE = CONFIG_FILE + ".bak"
WEB_HISTORY_LIMIT = 100
CONFIG_LOCK = threading.RLock()


def write_error_log(message):
    """Beklenmeyen hataları kalıcı dosyaya yazar (1 MB üstünde dosyayı döndürür)."""
    try:
        if os.path.exists(ERROR_LOG_FILE) and os.path.getsize(ERROR_LOG_FILE) > 1024 * 1024:
            os.replace(ERROR_LOG_FILE, ERROR_LOG_FILE + ".1")
        with open(ERROR_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except Exception:
        pass


def _global_excepthook(exc_type, exc, tb):
    write_error_log("Yakalanmamış hata:\n" + "".join(traceback.format_exception(exc_type, exc, tb)))
    try:
        ui_log(f"⚠️ Beklenmeyen hata: {exc}")
    except Exception:
        pass


sys.excepthook = _global_excepthook
try:
    threading.excepthook = lambda args: _global_excepthook(args.exc_type, args.exc_value, args.exc_traceback)
except Exception:
    pass


class UiBridge(QObject):
    """Arka thread'lerden GUI thread'ine güvenli köprü (Qt sinyalleri kuyruklu çalışır)."""
    log_signal = pyqtSignal(str)
    call_signal = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.call_signal.connect(self._run_call)

    def _run_call(self, fn):
        try:
            fn()
        except Exception as e:
            write_error_log("UI çağrısı hatası:\n" + traceback.format_exc())
            ui_log(f"⚠️ Arayüz hatası: {e}")


UI_BRIDGE = None
_PENDING_UI_LOGS = []


def _is_gui_thread():
    return threading.current_thread() is threading.main_thread()


def ui_log(message):
    """Her thread'den güvenle çağrılabilir; mesaj GUI thread'inde log alanına eklenir."""
    text = str(message)
    if UI_BRIDGE is None:
        _PENDING_UI_LOGS.append(text)
        return
    if _is_gui_thread():
        _append_log_now(text)
    else:
        UI_BRIDGE.log_signal.emit(text)


def _append_log_now(text):
    if MAIN_WINDOW is not None and hasattr(MAIN_WINDOW, "log_area"):
        MAIN_WINDOW.log_area.append(f"[{datetime.now().strftime('%H:%M:%S')}] {text}")
    else:
        _PENDING_UI_LOGS.append(text)


def run_on_ui(fn):
    """Bir fonksiyonu GUI thread'inde çalıştırır (web/makro thread'lerinden arayüz güncellemek için)."""
    if UI_BRIDGE is None or _is_gui_thread():
        fn()
    else:
        UI_BRIDGE.call_signal.emit(fn)


def init_ui_bridge():
    global UI_BRIDGE
    if UI_BRIDGE is None:
        UI_BRIDGE = UiBridge()
        UI_BRIDGE.log_signal.connect(_append_log_now)


def flush_pending_ui_logs():
    pending = list(_PENDING_UI_LOGS)
    _PENDING_UI_LOGS.clear()
    for text in pending:
        _append_log_now(text)


class TaskWorker:
    """
    Görevleri tek bir arka thread'de sırayla çalıştırır.
    - Arayüz donmaz; donma sırasında biriken tuşlar sonradan topluca çalışmaz.
    - Kuyrukta STALE_SECONDS'tan uzun bekleyen tuş görevleri atılır (ardarda tetiklenme engeli).
    - COM (pycaw) bu thread'de bir kez başlatılır.
    """
    STALE_SECONDS = 1.5

    def __init__(self):
        self.q = queue.Queue()
        self.thread = threading.Thread(target=self._loop, name="NexTaskWorker", daemon=True)
        self.thread.start()

    def submit(self, fn, *args, droppable=True):
        self.q.put((time.monotonic(), droppable, fn, args))

    def _loop(self):
        try:
            import comtypes
            comtypes.CoInitialize()
        except Exception:
            pass
        while True:
            queued_at, droppable, fn, args = self.q.get()
            try:
                waited = time.monotonic() - queued_at
                if droppable and waited > self.STALE_SECONDS:
                    ui_log(f"⏭️ Gecikmiş görev atlandı ({waited:.1f} sn bekledi)")
                    continue
                fn(*args)
            except Exception as e:
                write_error_log("Görev hatası:\n" + traceback.format_exc())
                ui_log(f"⚠️ Görev hatası: {e}")


TASK_WORKER = TaskWorker()

# ---------------------------------------------------------
# SendInput tabanlı tuş gönderimi
# keybd_event(scan=0) yerine gerçek scan code + kısa basılı tutma.
# OBS gibi tuşları periyodik yoklayan programlar ve DirectInput/RawInput
# kullanan oyunlar artık tuşu kaçırmaz.
# ---------------------------------------------------------
from ctypes import wintypes

INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
MAPVK_VK_TO_VSC_EX = 4
KEY_HOLD_SECONDS = 0.04
ULONG_PTR = ctypes.c_size_t


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", _KEYBDINPUT), ("mi", _MOUSEINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


# Medya/ses tuşlarının scan code karşılığı yok; bunlar VK ile gönderilir.
VK_ONLY_KEYS = {0xAD, 0xAE, 0xAF, 0xB0, 0xB1, 0xB2, 0xB3}
EXTENDED_VKS = {0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2C, 0x2D, 0x2E, 0x5B, 0x5C, 0x5D, 0x6F, 0x90, 0xA3, 0xA5}


def _send_key_event(vk, up=False):
    flags = KEYEVENTF_KEYUP if up else 0
    scan = 0
    if vk not in VK_ONLY_KEYS:
        try:
            scan_ex = ctypes.windll.user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC_EX)
        except Exception:
            scan_ex = 0
        scan = scan_ex & 0xFF
        if scan:
            flags |= KEYEVENTF_SCANCODE
            if (scan_ex >> 8) in (0xE0, 0xE1) or vk in EXTENDED_VKS:
                flags |= KEYEVENTF_EXTENDEDKEY
    inp = _INPUT(type=INPUT_KEYBOARD)
    inp.u.ki = _KEYBDINPUT(wVk=0 if (flags & KEYEVENTF_SCANCODE) else vk, wScan=scan, dwFlags=flags, time=0, dwExtraInfo=0)
    sent = ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))
    if sent != 1:
        # Yönetici olarak çalışan bir pencereye normal yetkiyle tuş gönderilemez (Windows UIPI).
        raise OSError("Tuş gönderilemedi. Hedef uygulama yönetici olarak çalışıyor olabilir; NexStudio'yu da yönetici olarak çalıştırın.")


def send_key_combo(vk_list, hold=KEY_HOLD_SECONDS):
    pressed = []
    try:
        for vk in vk_list:
            _send_key_event(vk)
            pressed.append(vk)
            time.sleep(0.01)
        time.sleep(hold)
    finally:
        for vk in reversed(pressed):
            try:
                _send_key_event(vk, up=True)
            except Exception:
                pass
            time.sleep(0.005)


def is_process_elevated():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


_SINGLE_INSTANCE_HANDLE = None


def acquire_single_instance():
    """
    Aynı anda iki NexStudio açılırsa ikisi de aynı COM portunu kapmaya çalışır ve
    tuşlar 'bazen' çalışmaz. Windows named mutex ile tek kopya garantilenir.
    """
    global _SINGLE_INSTANCE_HANDLE
    try:
        name = "Local\\NexStudio_SingleInstance_" + hashlib.md5(APP_DIR.lower().encode("utf-8")).hexdigest()[:12]
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        _SINGLE_INSTANCE_HANDLE = kernel32.CreateMutexW(None, False, name)
        return ctypes.get_last_error() != 183  # ERROR_ALREADY_EXISTS
    except Exception:
        return True


def release_single_instance():
    global _SINGLE_INSTANCE_HANDLE
    if _SINGLE_INSTANCE_HANDLE:
        try:
            ctypes.windll.kernel32.CloseHandle(_SINGLE_INSTANCE_HANDLE)
        except Exception:
            pass
        _SINGLE_INSTANCE_HANDLE = None


def relaunch_as_admin():
    """Uygulamayı yönetici olarak yeniden başlatır (UAC onayı istenir)."""
    if getattr(sys, "frozen", False):
        exe, params = sys.executable, " ".join(f'"{a}"' for a in sys.argv[1:])
    else:
        exe, params = sys.executable, " ".join(f'"{a}"' for a in sys.argv)
    rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
    return rc > 32

# =========================================================
# 3. DİL SİSTEMİ (ÇEVİRİLER)
# =========================================================
DEFAULT_TRANSLATIONS = {
    "tr": {
        "lang_name": "Türkçe",
        "tab_physical": "Fiziksel Tuşlar", "tab_screen": "Dokunmatik Ekran",
        "tab_log": "Sistem Günlüğü", "tab_settings": "Ayarlar", "tab_account": "Hesap & Bulut",
        "refresh": "🔄 Yenile", "connect": "Bağlan", "disconnect": "Bağlantıyı Kes",
        "device_not_found": "Cihaz Bulunamadı", "select_key": "Lütfen soldan bir tuş seçin",
        "category": "Kategori / Eklenti:", "task": "Görev Seçimi:", "current_assign": "Mevcut Atama:",
        "save_key": "💾 Bu Tuşa Kaydet", "screen_page": "Ekran Sayfası:", "add_bg": "🖼️ Ekrana Arka Plan Görseli Ekle",
        "screen_text": "Ekranda Görünecek Yazı:", "save_screen": "💾 Ekran Butonuna Kaydet",
        "appearance": "Görünüm", "accent_color": "Uygulama Vurgu Rengi:",
        "choose_color": "Renk Seç", "reset_color": "Varsayılan renge dön", "system": "Sistem", "start_win": "Windows ile Başlat", "run_bg": "Kapatınca Arka Planda Çalış",
        "mobile_server": "📱 Mobil Sunucuyu Başlat", "mobile_stop": "📱 Mobil Sunucuyu Durdur",
        "language": "Uygulama Dili:", "plugin_manage": "Eklenti (Plugin) Yönetimi", "open_plugins": "📂 Eklenti Klasörünü Aç",
        "open_locales": "🌍 Dil Klasörünü Aç", "danger_zone": "Tehlikeli Bölge", "factory_reset": "⚠️ Tüm Tuşları Fabrika Ayarlarına Sıfırla",
        "success": "Başarılı", "saved": "Ayarlar başarıyla kaydedildi!", "saved_short": "Kaydedildi",
        "reset_confirm": "Tüm tuş atamaları silinecek ve fabrika ayarlarına dönülecek. Emin misiniz?",
        "btn_1": "🔘 1. Buton (Kısa)", "btn_2": "🔘 2. Buton (Kısa)", "btn_3": "🔘 3. Buton (Kısa)", "btn_4": "🔘 4. Buton (Kısa)", "btn_5": "🔘 5. Buton (Kısa)", 
        "btn_1_l": "🔘 1. Buton (Uzun)", "btn_2_l": "🔘 2. Buton (Uzun)", "btn_3_l": "🔘 3. Buton (Uzun)", "btn_4_l": "🔘 4. Buton (Uzun)", "btn_5_l": "🔘 5. Buton (Uzun)", 
        "enc_up": "🎛️ Tekerlek (Sağa Çevir)", "enc_down": "🎛️ Tekerlek (Sola Çevir)", "enc_btn": "🎛️ Tekerlek Butonu (Bas)",
        "cat_custom": "Özel Kısayollar", "act_custom_web": "Özel Web Sitesi Aç", "act_custom_app": "Özel Uygulama / Dosya İşlemi", "act_custom_hotkey": "Özel Tuş Kombinasyonu (Kısayol)",
        "cat_text": "Metin Yazdırma", "act_text_type": "Otomatik Metin Yaz (Şifre vb.)",
        "cat_fkeys": "F Tuşları (Sanal Makro)", "cat_numpad": "Numpad Tuşları",
        "cat_media": "Genel Medya Kontrolleri", "act_media_pp": "Oynat/Duraklat", "act_media_next": "Sonraki Şarkı", "act_media_prev": "Önceki Şarkı", "act_media_mute": "Sesi Kapat",
        "cat_vol": "Ses Seviyesi Kontrolleri", "act_vol_up": "Genel Sesi Artır (+%1)", "act_vol_down": "Genel Sesi Azalt (-%1)", "act_vol_foc_up": "Aktif Pencere Sesini Artır", "act_vol_foc_down": "Aktif Pencere Sesini Azalt",
        "cat_web": "Web Siteleri", "act_web_yt": "YouTube Aç", "act_web_kick": "Kick Aç",
        "cat_tools": "Sistem Araçları", "act_tool_exp": "Dosya Gezgini", "act_tool_calc": "Hesap Makinesi", "act_tool_task": "Görev Yöneticisi",
        "cat_power": "Güç Seçenekleri", "act_pow_sleep": "Uyku Modu", "act_pow_shut": "Bilgisayarı Kapat", "act_pow_res": "Yeniden Başlat", "act_pow_lock": "Bilgisayarı Kilitle",
        "cat_win": "Pencere Yönetimi", "act_win_max": "Tam Ekran Yap", "act_win_min": "Aşağı İndir", "act_win_left": "Sola Yasla", "act_win_right": "Sağa Yasla", "act_win_next": "Diğer Ekrana Taşı", "act_win_d": "Tüm Pencereleri Küçült",
        "cat_snip": "Ekran Alıntısı", "act_snip_reg": "Bölge Seçerek Kırp", "act_snip_full": "Tam Ekranı Kaydet", "act_snip_app": "Ekran Alıntısı Aracını Aç",
        "page_1": "Yayın Kontrolleri", "page_2": "Medya & Ekstra", "page_3": "Dinamik Yazı", "page_4": "Dinamik Yazı",
        "btn_next": "İleri ➔", "btn_prev": "🡄 Geri", "empty": "Boş", "no_action": "İşlem Yok",
        "placeholder_readonly": "Sayfa 1 ve 2'de yazı değiştirilemez", "placeholder_text": "Örn: Spotify",
        "placeholder_web": "Örn: https://google.com", "placeholder_app": "Örn: C:\\Programlar\\uygulama.exe", "placeholder_shortcut": "Örn: ctrl+shift+s",
        "placeholder_type_text": "Örn: BenimGizliSifrem123",
        "log_signal": "Sinyal:", "log_error": "Makro Hatası:", "app_prefix": "Uygulama:",
        "edit_page_name": "Sayfa Adını Değiştir", "prompt_page_name": "Yeni sayfa adını girin:",
        "screen_selected": "Seçili Buton:",
        "turn_func": "Tekerlek Çevirme İşlevi:", "find_apps": "🔄 Uygulamaları Bul",
        "general_vol": "Genel Ses Seviyesi", "active_vol": "Aktif Pencere Sesi", "brightness": "Ekran Parlaklığı",
        "app_vol_header": "Uygulama Sesleri (Windows Ses Karıştırıcısı)", "refresh_audio_apps": "🔄 Ses Uygulamalarını Yenile", "no_audio_apps": "Ses çalan uygulama bulunamadı",
        "browser_def": "Varsayılan Tarayıcı", "browser_chr": "Google Chrome", "browser_edg": "Microsoft Edge", "browser_fir": "Mozilla Firefox",
        "app_open": "Uygulamayı Aç", "app_close": "Uygulamayı Kapat", "app_force": "Zorla Kapat (Görev Yöneticisi)",
        "web_tab_ctrl": "Kontrol", "web_tab_assign": "Atama Yap", "web_tab_set": "Ayarlar",
        "web_phys": "Fiziksel Tuşlar", "web_scr": "Dokunmatik Ekran", "web_which_key": "Hangi Tuş?",
        "web_save": "💾 Kaydet", "web_saved": "Başarıyla Kaydedildi!", "web_page_names": "Sayfa İsimlerini Düzenle",
        "scan_apps": "🔍 Yüklü Uygulamaları Tara", "help_btn": "❓ Kullanım Rehberi & Yardım",
        "acc_title": "NexStudio Bulut Hesabı (Geliştirme Aşamasında)", "acc_desc": "Bu özellik yakında aktif olacaktır. Ayarlarınızı buluta yedeklemek ve resmi web sitesiyle eşitlemek için kullanabileceksiniz.",
        "acc_email": "E-Posta Adresi", "acc_pass": "Şifre", "acc_login": "Giriş Yap", "acc_register": "Kayıt Ol",
        "acc_logged_in": "✅ Bulut Eşitlemesi Aktif (Bağlı Hesap: {})",
        "brand_subtitle": "NexDeck kontrol merkezi",
        "home": "Başlangıç",
        "device_status": "Cihaz Durumu",
        "status_waiting": "● Cihaz bekleniyor",
        "status_connected": "● Cihaz bağlı",
        "sidebar_status_hint": "Bağlantı kurulduğunda tuşlar ve ekran atamaları cihazla eşitlenir.",
        "page_sub_home": "Cihazını bağla, tuşları özelleştir ve ekran sayfalarını yönet.",
        "home_title": "NexDeck kontrol merkezi",
        "home_desc": "Tuş atama, dokunmatik ekran sayfaları, tekerlek kontrolü ve web kontrol altyapısı tek panelde.",
        "edit_physical_keys": "Fiziksel tuşları düzenle",
        "screen_pages": "Ekran sayfaları",
        "quick_status": "Güncelleme Rehberi",
        "quick_physical": "• Arayüz sadeleştirildi, ikonlar ve başlıklar düzenlendi.",
        "quick_screen": "• Tekerlek ayarı artık yalnızca Tekerlek Butonu içinde yönetiliyor.",
        "quick_mixer": "• Ses kontrolü %1 adımlı ve Windows ses karıştırıcısı uyumlu hale getirildi.",
        "quick_mobile": "• Web Kontrolü ve Hesap özellikleri geliştirme aşamasında hazırlanıyor.",
        "tab_web": "Web Kontrolü", "page_sub_web": "Cihaz bağlı olmasa bile mobil atama ve web kontrol özelliklerini buradan yönet.",
        "web_control_title": "Web Kontrolü", "web_control_desc": "Web Kontrolü ile cihaz bağlı olmasa bile telefondan atama ve kontrol işlemleri yapılabilir.",
        "dev_stage": "Geliştirme Aşamasında", "account_dev_desc": "Hesap & Bulut bölümü geliştirme aşamasındadır. Şu an yalnızca bilgilendirme amaçlı gösterilir.",
        "settings_button": "Ayarlar", "wheel_label": "Tekerlek",
        "card_phys_desc": "Kısa/uzun basım görevlerini değiştir.",
        "card_screen_desc": "Ekran butonlarını sayfa sayfa düzenle.",
        "card_encoder_desc": "Ses, parlaklık veya uygulama sesi için tekerlek davranışını seç.",
        "card_settings_desc": "Tema, dil, sistem ve geliştirme seçeneklerini yönet.",
        "page_sub_physical": "Fiziksel tuşlara görev ata; tekerlek butonu seçilince çevirme işlevini alttan yönet.",
        "page_sub_screen": "Dokunmatik ekran sayfalarını cihaz önizlemesi üzerinden yapılandır.",
        "page_sub_log": "Cihazdan gelen sinyalleri ve makro durumlarını canlı takip et.",
        "page_sub_settings": "Tema, dil, sistem ve geliştirme aşamasındaki hesap seçeneklerini yönet.",
        "page_sub_account": "Web kontrolü ve mobil erişim özellikleri için hazırlanan alan.",
        "device_keys": "Cihaz Tuşları",
        "device_keys_hint": "Önce soldan bir tuş seç, ardından sağdaki panelden görevini belirle.",
        "assign_task": "Görev Atama",
        "encoder_hint": "Tekerleği sağa/sola çevirdiğinde yapılacak işlem:",
        "error": "Hata",
        "confirm": "Onay",
        "no_installed_app": "Uygulama bulunamadı.",
        "select_app": "Uygulama Seç",
        "select_app_prompt": "Listeden bir uygulama seçin:",
        "screen_page_title": "Ekran Sayfası",
        "background": "Arka Plan",
        "display_preview": "NexDeck ekran önizlemesi",
        "button_appearance": "Buton Görünümü",
        "button_label": "Buton {}",
        "page_label": "Sayfa {}",
        "choose_bg": "Arka Plan Seç",
        "image_files": "Resim Dosyaları (*.png *.jpg *.jpeg)",
        "live_log": "Canlı Sistem Günlüğü",
        "live_log_hint": "Cihazdan gelen sinyaller, atanan makrolar ve hata mesajları burada görünür.",
        "toggle_qr": "👁️ QR Kodu Göster/Gizle",
        "restart_app": "🔄 Uygulamayı Yeniden Başlat",
        "account_desc": "Bu bölüm geliştirme aşamasındadır. Gelecekte ayarlarınızı buluta yedekleyebilecek ve hesabınızla senkronize edebileceksiniz.",
        "help_title": "NexStudio Kullanım Rehberi",
        "help_video": "▶️ NexHub kanalına git ve kullanım videosunu izle",
        "help_html": "<b>1. Fiziksel Tuşlar:</b><br>Mekanik tuşlara kısa ve uzun basım görevleri atayabilirsiniz.<br><br><b>2. Dokunmatik Ekran:</b><br>Ekran sayfalarını düzenleyebilir ve desteklenen alanlarda metinleri değiştirebilirsiniz.<br><br><b>3. Web Kontrolü:</b><br>Cihaz bağlı olmasa bile telefonundan tuş ataması yapabilir ve kontrolleri uzaktan çalıştırabilirsin.<br><br><b>4. Eklentiler:</b><br>Ayarlar bölümünden eklenti klasörünü açarak yeni .py dosyaları ekleyebilirsiniz.",
        "pin_code": "PIN Kodunuz: {}",
        "qr_missing": "URL: {} (QR için 'qrcode' kütüphanesini kurun)",
        "connected_log": "[+] NexDeck cihazına bağlanıldı.",
        "found_task": "▶ Görev Bulundu: {}",
        "no_assigned_task": "⚠️ Bu tuşa atanmış görev yok.",
        "audio_apps_refresh_log": "🔄 Windows ses karıştırıcısı uygulamaları yenilendi.",
        "audio_apps_error": "⚠️ Ses uygulamaları listelenemedi: {}",
        "encoder_changed_log": "🎛️ Tekerlek işlevi değiştirildi: {}",
        "saved_app_suffix": "{} (kayıtlı)",
        "audio_session_not_found": "⚠️ Ses oturumu bulunamadı. Uygulama ses çalıyor mu veya doğru pencere aktif mi?",
        "volume_error": "⚠️ Ses Hatası: {}",
        "master_volume_fallback": "⚠️ Genel ses pycaw hatası, yedek yönteme geçiliyor: {}",
        "startup_error": "Startup ayarı yapılamadı:",
        "tray_show": "Göster",
        "tray_exit": "Çıkış",
        "running_bg": "Uygulama arka planda çalışıyor."
    },
    "en": {
        "lang_name": "English",
        "tab_physical": "Physical Keys", "tab_screen": "Touch Screen",
        "tab_log": "System Log", "tab_settings": "Settings", "tab_account": "Account & Cloud",
        "refresh": "🔄 Refresh", "connect": "Connect", "disconnect": "Disconnect",
        "device_not_found": "Device Not Found", "select_key": "Please select a key from the left",
        "category": "Category / Plugin:", "task": "Task Selection:", "current_assign": "Current Assignment:",
        "save_key": "💾 Save to this Key", "screen_page": "Screen Page:", "add_bg": "🖼️ Add Background Image",
        "screen_text": "Text on Screen:", "save_screen": "💾 Save Screen Button",
        "appearance": "Appearance", "accent_color": "App Accent Color:",
        "choose_color": "Choose Color", "reset_color": "Reset color", "system": "System", "start_win": "Start with Windows", "run_bg": "Run in Background",
        "mobile_server": "📱 Start Mobile Server", "mobile_stop": "📱 Stop Mobile Server",
        "language": "App Language:", "plugin_manage": "Plugin Management", "open_plugins": "📂 Open Plugin Folder",
        "open_locales": "🌍 Open Language Folder", "danger_zone": "Danger Zone", "factory_reset": "⚠️ Factory Reset All Keys",
        "success": "Success", "saved": "Settings saved successfully!", "saved_short": "Saved",
        "reset_confirm": "All key assignments will be deleted and factory settings will be restored. Are you sure?",
        "btn_1": "🔘 Button 1 (Short)", "btn_2": "🔘 Button 2 (Short)", "btn_3": "🔘 Button 3 (Short)", "btn_4": "🔘 Button 4 (Short)", "btn_5": "🔘 Button 5 (Short)", 
        "btn_1_l": "🔘 Button 1 (Long)", "btn_2_l": "🔘 Button 2 (Long)", "btn_3_l": "🔘 Button 3 (Long)", "btn_4_l": "🔘 Button 4 (Long)", "btn_5_l": "🔘 Button 5 (Long)", 
        "enc_up": "🎛️ Wheel (Turn Right)", "enc_down": "🎛️ Wheel (Turn Left)", "enc_btn": "🎛️ Wheel Button (Press)",
        "cat_custom": "Custom Shortcuts", "act_custom_web": "Open Custom Website", "act_custom_app": "Custom App / File Action", "act_custom_hotkey": "Custom Key Combination (Shortcut)",
        "cat_text": "Text Typing", "act_text_type": "Auto-type Text (Password etc.)",
        "cat_fkeys": "F Keys (Virtual Macro)", "cat_numpad": "Numpad Keys",
        "cat_media": "General Media Controls", "act_media_pp": "Play/Pause", "act_media_next": "Next Track", "act_media_prev": "Previous Track", "act_media_mute": "Mute Volume",
        "cat_vol": "Volume Controls", "act_vol_up": "Volume Up (+1%)", "act_vol_down": "Volume Down (-1%)", "act_vol_foc_up": "Active Window Vol Up", "act_vol_foc_down": "Active Window Vol Down",
        "cat_web": "Websites", "act_web_yt": "Open YouTube", "act_web_kick": "Open Kick",
        "cat_tools": "System Tools", "act_tool_exp": "File Explorer", "act_tool_calc": "Calculator", "act_tool_task": "Task Manager",
        "cat_power": "Power Options", "act_pow_sleep": "Sleep", "act_pow_shut": "Shutdown", "act_pow_res": "Restart", "act_pow_lock": "Lock Computer",
        "cat_win": "Window Management", "act_win_max": "Maximize", "act_win_min": "Minimize", "act_win_left": "Snap Left", "act_win_right": "Snap Right", "act_win_next": "Move to Next Monitor", "act_win_d": "Minimize All Windows",
        "cat_snip": "Snipping Tool", "act_snip_reg": "Snip Region", "act_snip_full": "Save Full Screen", "act_snip_app": "Open Snipping Tool",
        "page_1": "Stream Controls", "page_2": "Media & Extra", "page_3": "Dynamic Text", "page_4": "Dynamic Text",
        "btn_next": "Next ➔", "btn_prev": "🡄 Prev", "empty": "Empty", "no_action": "No Action",
        "placeholder_readonly": "Text cannot be changed on Page 1 and 2", "placeholder_text": "Ex: Spotify",
        "placeholder_web": "Ex: https://google.com", "placeholder_app": "Ex: C:\\Programs\\app.exe", "placeholder_shortcut": "Ex: ctrl+shift+s",
        "placeholder_type_text": "Ex: MySecretPassword123",
        "log_signal": "Signal:", "log_error": "Macro Error:", "app_prefix": "App:",
        "edit_page_name": "Change Page Name", "prompt_page_name": "Enter new page name:",
        "screen_selected": "Selected Button:",
        "turn_func": "Wheel Function:", "find_apps": "🔄 Find Apps",
        "general_vol": "General Volume", "active_vol": "Active Window Volume", "brightness": "Screen Brightness",
        "app_vol_header": "App Volumes (Windows Volume Mixer)", "refresh_audio_apps": "🔄 Refresh Audio Apps", "no_audio_apps": "No audio app found",
        "browser_def": "Default Browser", "browser_chr": "Google Chrome", "browser_edg": "Microsoft Edge", "browser_fir": "Mozilla Firefox",
        "app_open": "Open App", "app_close": "Close App", "app_force": "Force Close (Taskkill)",
        "web_tab_ctrl": "Control", "web_tab_assign": "Assign Key", "web_tab_set": "Settings",
        "web_phys": "Physical Keys", "web_scr": "Touch Screen", "web_which_key": "Which Key?",
        "web_save": "💾 Save", "web_saved": "Saved Successfully!", "web_page_names": "Edit Page Names",
        "scan_apps": "🔍 Scan Installed Apps", "help_btn": "❓ Help & User Guide",
        "acc_title": "NexStudio Cloud Account (Coming Soon)", "acc_desc": "This feature will be active soon. You will be able to backup your settings to the cloud and sync with the official website.",
        "acc_email": "Email Address", "acc_pass": "Password", "acc_login": "Login", "acc_register": "Register",
        "acc_logged_in": "✅ Cloud Sync Active (Linked Account: {})",
        "brand_subtitle": "NexDeck control center",
        "home": "Home",
        "device_status": "Device Status",
        "status_waiting": "● Device waiting",
        "status_connected": "● Device connected",
        "sidebar_status_hint": "When connected, key and screen assignments are synchronized with the device.",
        "page_sub_home": "Connect your device, customize keys, and manage screen pages.",
        "home_title": "NexDeck control center",
        "home_desc": "Key assignments, touch screen pages, encoder volume control, and mobile control in one panel.",
        "edit_physical_keys": "Edit physical keys",
        "screen_pages": "Screen pages",
        "quick_status": "Update Guide",
        "quick_physical": "• The interface was simplified and the icons/headings were cleaned up.",
        "quick_screen": "• Wheel settings are now managed only from the Wheel Button panel.",
        "quick_mixer": "• Volume control now uses 1% steps and works with the Windows volume mixer.",
        "quick_mobile": "• Web Control and Account features are currently being prepared.",
        "tab_web": "Web Control", "page_sub_web": "Manage mobile assignment and web control features here, even without the device connected.",
        "web_control_title": "Web Control", "web_control_desc": "Web Control can be used from your phone for assignments and remote controls, even when the device is not connected.",
        "dev_stage": "In Development", "account_dev_desc": "The Account & Cloud area is under development and is currently shown for information only.",
        "settings_button": "Settings", "wheel_label": "Wheel",
        "card_phys_desc": "Change short/long press tasks.",
        "card_screen_desc": "Edit screen buttons page by page.",
        "card_encoder_desc": "Select volume, brightness, or app audio.",
        "card_settings_desc": "Theme, language, mobile server, and plugins.",
        "page_sub_physical": "Assign tasks to physical keys; manage wheel turning when the wheel button is selected.",
        "page_sub_screen": "Configure touch screen pages from the device preview.",
        "page_sub_log": "Monitor device signals and macro status live.",
        "page_sub_settings": "Manage theme, language, system, and in-development account options.",
        "page_sub_account": "Area prepared for web control and mobile access features.",
        "device_keys": "Device Keys",
        "device_keys_hint": "Select a key on the left, then choose its task from the panel on the right.",
        "assign_task": "Task Assignment",
        "encoder_hint": "Action to perform when the wheel is turned left/right:",
        "error": "Error",
        "confirm": "Confirmation",
        "no_installed_app": "No app found.",
        "select_app": "Select App",
        "select_app_prompt": "Select an app from the list:",
        "screen_page_title": "Screen Page",
        "background": "Background",
        "display_preview": "NexDeck display preview",
        "button_appearance": "Button Appearance",
        "button_label": "Button {}",
        "page_label": "Page {}",
        "choose_bg": "Choose Background",
        "image_files": "Image Files (*.png *.jpg *.jpeg)",
        "live_log": "Live System Log",
        "live_log_hint": "Device signals, assigned macros, and error messages appear here.",
        "toggle_qr": "👁️ Show/Hide QR Code",
        "restart_app": "🔄 Restart App",
        "account_desc": "This section is under development. In the future, you will be able to back up your settings to the cloud and sync them with your account.",
        "help_title": "NexStudio User Guide",
        "help_video": "▶️ Open NexHub channel and watch the tutorial",
        "help_html": "<b>1. Physical Keys:</b><br>You can assign different tasks to mechanical keys for short and long presses.<br><br><b>2. Touch Screen:</b><br>You can edit screen pages and change button text on supported pages.<br><br><b>3. Plugins:</b><br>You can open the plugin folder from Settings and add new .py files.<br><br><b>4. Mobile Control:</b><br>Start the mobile server and scan the QR code to control your device from your phone.",
        "pin_code": "Your PIN Code: {}",
        "qr_missing": "URL: {} (Install the 'qrcode' library for QR support)",
        "connected_log": "[+] Connected to NexDeck device.",
        "found_task": "▶ Task Found: {}",
        "no_assigned_task": "⚠️ No task assigned to this key.",
        "audio_apps_refresh_log": "🔄 Windows volume mixer apps refreshed.",
        "audio_apps_error": "⚠️ Audio apps could not be listed: {}",
        "encoder_changed_log": "🎛️ Wheel function changed: {}",
        "saved_app_suffix": "{} (saved)",
        "audio_session_not_found": "⚠️ Audio session not found. Is the app playing audio or is the correct window active?",
        "volume_error": "⚠️ Volume Error: {}",
        "master_volume_fallback": "⚠️ Master volume pycaw error, switching to fallback method: {}",
        "startup_error": "Startup setting could not be applied:",
        "tray_show": "Show",
        "tray_exit": "Exit",
        "running_bg": "App is running in the background."
    }
}

TRANSLATIONS = {}
TEXT_ONLY_LOCALE_KEYS = [
    "home",
    "tab_physical",
    "tab_screen",
    "tab_log",
    "tab_settings",
    "tab_account",
    "tab_web",
    "edit_physical_keys",
    "screen_pages",
    "device_keys",
    "device_status",
    "quick_status",
    "quick_physical",
    "quick_screen",
    "quick_mixer",
    "quick_mobile",
    "home_desc",
    "card_encoder_desc",
    "card_settings_desc",
    "brand_subtitle",
    "page_sub_home",
    "page_sub_physical",
    "page_sub_screen",
    "page_sub_log",
    "page_sub_settings",
    "page_sub_account",
    "page_sub_web",
    "settings_button",
    "wheel_label",
    "account_desc",
    "account_dev_desc",
    "web_control_title",
    "web_control_desc",
    "dev_stage",
]

def load_locales():
    global TRANSLATIONS
    TRANSLATIONS = {}
    for lang, data in DEFAULT_TRANSLATIONS.items():
        TRANSLATIONS[lang] = data.copy()
    for file in glob.glob(os.path.join(LOCALES_DIR, "*.json")):
        lang_code = os.path.basename(file).split(".")[0]
        try:
            with open(file, "r", encoding="utf-8") as f:
                file_data = json.load(f)
                if lang_code in TRANSLATIONS:
                    # 2.0: Uygulamanın kendi metinleri her zaman güncel kalsın diye varsayılanlar önceliklidir.
                    # Dosya sadece eksik anahtarları tamamlar (eski sürümden kalan metinler yeni sürümü ezmez).
                    for key, value in file_data.items():
                        TRANSLATIONS[lang_code].setdefault(key, value)
                else:
                    TRANSLATIONS[lang_code] = file_data
        except:
            pass

    # Eski locale dosyalarındaki ikonlu metinler yeni UI ile çakışmasın diye
    # bazı ana başlıkları varsayılan, yazı-odaklı halleriyle zorla senkronla.
    for lang_code, lang_data in TRANSLATIONS.items():
        default_pack = DEFAULT_TRANSLATIONS.get(lang_code, DEFAULT_TRANSLATIONS.get("tr", {}))
        for key in TEXT_ONLY_LOCALE_KEYS:
            if key in default_pack:
                lang_data[key] = default_pack[key]

    for lang_code, lang_data in TRANSLATIONS.items():
        with open(os.path.join(LOCALES_DIR, f"{lang_code}.json"), "w", encoding="utf-8") as f:
            json.dump(lang_data, f, indent=4, ensure_ascii=False)

APP_CONFIG = {}
def tr(key):
    lang = APP_CONFIG.get("language", "tr")
    if lang in TRANSLATIONS and key in TRANSLATIONS[lang]:
        return TRANSLATIONS[lang][key]
    return DEFAULT_TRANSLATIONS["tr"].get(key, key)

# =========================================================
# 4. WINDOWS API VE NATIVE MAKROLAR
# =========================================================
VK_MEDIA_NEXT_TRACK, VK_MEDIA_PREV_TRACK, VK_MEDIA_PLAY_PAUSE, VK_VOLUME_MUTE = 0xB0, 0xB1, 0xB3, 0xAD
VK_VOLUME_UP, VK_VOLUME_DOWN = 0xAF, 0xAE
VK_F13, VK_F14, VK_F15, VK_F16 = 0x7C, 0x7D, 0x7E, 0x7F
VK_F17, VK_F18, VK_F19, VK_F20 = 0x80, 0x81, 0x82, 0x83
VK_F21, VK_F22, VK_F23, VK_F24 = 0x84, 0x85, 0x86, 0x87

VK_MAP = {
    'ctrl': 0x11, 'shift': 0x10, 'alt': 0x12, 'win': 0x5B, 'enter': 0x0D, 'space': 0x20, 'tab': 0x09, 'esc': 0x1B, 'backspace': 0x08,
    'print screen': 0x2C, 'printscreen': 0x2C, 'prtsc': 0x2C,
    'up': 0x26, 'down': 0x28, 'left': 0x25, 'right': 0x27,
    'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45, 'f': 0x46, 'g': 0x47, 'h': 0x48, 'i': 0x49, 'j': 0x4A, 'k': 0x4B, 'l': 0x4C, 'm': 0x4D, 'n': 0x4E, 'o': 0x4F, 'p': 0x50, 'q': 0x51, 'r': 0x52, 's': 0x53, 't': 0x54, 'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58, 'y': 0x59, 'z': 0x5A,
    '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34, '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
    'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73, 'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77, 'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
    'f13': 0x7C, 'f14': 0x7D, 'f15': 0x7E, 'f16': 0x7F, 'f17': 0x80, 'f18': 0x81, 'f19': 0x82, 'f20': 0x83, 'f21': 0x84, 'f22': 0x85, 'f23': 0x86, 'f24': 0x87,
    'control': 0x11, 'windows': 0x5B, 'escape': 0x1B, 'return': 0x0D,
    'delete': 0x2E, 'del': 0x2E, 'insert': 0x2D, 'ins': 0x2D, 'home': 0x24, 'end': 0x23,
    'pageup': 0x21, 'page up': 0x21, 'pgup': 0x21, 'pagedown': 0x22, 'page down': 0x22, 'pgdn': 0x22,
    '`': 0xC0
}

# Windows VK -> USB HID usage kodu. Cihaz "USB klavye" modunda bu kodları gerçek klavye gibi basar.
# Firmware: kod >= 0xE0 ise modifier (Ctrl/Shift/Alt/Win), değilse normal tuş.
HID_KEY_CODES = {
    0x11: 0xE0, 0x10: 0xE1, 0x12: 0xE2, 0x5B: 0xE3,
    0x0D: 0x28, 0x1B: 0x29, 0x08: 0x2A, 0x09: 0x2B, 0x20: 0x2C, 0x2C: 0x46,
    0x2D: 0x49, 0x24: 0x4A, 0x21: 0x4B, 0x2E: 0x4C, 0x23: 0x4D, 0x22: 0x4E,
    0x27: 0x4F, 0x25: 0x50, 0x28: 0x51, 0x26: 0x52,
    0x6F: 0x54, 0x6A: 0x55, 0x6D: 0x56, 0x6B: 0x57, 0x60: 0x62, 0x6E: 0x63,
    0xC0: 0x35,
}
HID_KEY_CODES.update({0x41 + i: 0x04 + i for i in range(26)})              # A-Z
HID_KEY_CODES.update({0x31 + i: 0x1E + i for i in range(9)})               # 1-9
HID_KEY_CODES[0x30] = 0x27                                                  # 0
HID_KEY_CODES.update({0x70 + i: 0x3A + i for i in range(12)})              # F1-F12
HID_KEY_CODES.update({0x7C + i: 0x68 + i for i in range(12)})              # F13-F24
HID_KEY_CODES.update({0x61 + i: 0x59 + i for i in range(9)})               # Numpad 1-9

def press_key(vk_code):
    send_key_combo([vk_code])

def get_physical_buttons():
    return {
        "BTN:1": tr("btn_1"), "BTN:2": tr("btn_2"), "BTN:3": tr("btn_3"), "BTN:4": tr("btn_4"), "BTN:5": tr("btn_5"), 
        "BTN:1:LONG": tr("btn_1_l"), "BTN:2:LONG": tr("btn_2_l"), "BTN:3:LONG": tr("btn_3_l"), "BTN:4:LONG": tr("btn_4_l"), "BTN:5:LONG": tr("btn_5_l"), 
        "ENC:BTN": tr("enc_btn")
    }

# Nextion ekrandan GELEN GERÇEK sinyaller.
# Bundan sonra dokunmatik görevleri bu sinyal adlarına göre kaydedilir ve çalıştırılır.
# Fiziksel tuşlar/encoder bu yapıdan bağımsızdır.
TOUCH_PAGE_SIGNALS = {
    1: [
        "NEX:MIC_TOGGLE",
        "NEX:DESK_TOGGLE",
        "NEX:CAM_TOGGLE",
        "NEX:LIVE_TOGGLE",
        "NEX:SCENE_1",
        "NEX:SCENE_2",
        "NEX:SCENE_3",
    ],
    2: [
        "NEX:MEDIA_PREV",
        "NEX:MEDIA_PP",
        "NEX:MEDIA_NEXT",
        "NEX:REC_TOGGLE",
        "NEX:OPEN_YT",
        "NEX:OPEN_KICK",
    ],
    3: [
        "NEX:P3_B1",
        "NEX:P3_B2",
        "NEX:P3_B3",
        "NEX:P3_B4",
        "NEX:P3_B5",
        "NEX:P3_B6",
    ],
    4: [
        "NEX:P4_B1",
        "NEX:P4_B2",
        "NEX:P4_B3",
        "NEX:P4_B4",
        "NEX:P4_B5",
        "NEX:P4_B6",
    ],
}

# UI'da 8 slot var; bazı slotlar ileri/geri sayfa tuşu ve görev almaz.
# Bu eşleşme sadece uygulamadaki görsel slotu gerçek Nextion görev sinyaline bağlar.
TOUCH_UI_SLOT_TO_SIGNAL = {
    1: {
        0: "NEX:MIC_TOGGLE",
        1: "NEX:DESK_TOGGLE",
        2: "NEX:CAM_TOGGLE",
        3: "NEX:LIVE_TOGGLE",
        4: "NEX:SCENE_1",
        5: "NEX:SCENE_2",
        6: "NEX:SCENE_3",
    },
    2: {
        0: "NEX:MEDIA_PREV",
        1: "NEX:MEDIA_PP",
        2: "NEX:MEDIA_NEXT",
        3: "NEX:REC_TOGGLE",
        # slot 4 geri tuşudur
        5: "NEX:OPEN_YT",
        6: "NEX:OPEN_KICK",
        # slot 7 ileri tuşudur
    },
    3: {
        0: "NEX:P3_B1",
        1: "NEX:P3_B2",
        2: "NEX:P3_B3",
        3: "NEX:P3_B4",
        # slot 4 geri tuşudur
        5: "NEX:P3_B5",
        6: "NEX:P3_B6",
        # slot 7 ileri tuşudur
    },
    4: {
        0: "NEX:P4_B1",
        1: "NEX:P4_B2",
        2: "NEX:P4_B3",
        3: "NEX:P4_B4",
        # slot 4 geri tuşudur
        5: "NEX:P4_B5",
        6: "NEX:P4_B6",
        # slot 7 ileri tuşudur / son sayfada pasif
    },
}

# Sayfa 3-4'te ekrana yazı göndermek için UI slotundan gerçek Nextion obje adına gideriz.
# Bu sadece ekran yazısı güncelleme içindir; görev çalıştırma için sinyal çevrilmez.
NEXTION_TEXT_OBJ_BY_SLOT = {
    # Sadece Nextion ekranındaki yazıları güncellemek için kullanılır.
    # Görev çalıştırma tarafı cihazdan gelen gerçek sinyalleri kullanır.
    3: {
        0: "b0",
        1: "b1",
        2: "b2",
        3: "b3",
        5: "b4",  # P3_B5
        6: "b5",  # P3_B6; b6 ileri tuşu olduğu için buraya yazılmamalı
    },
    4: {
        0: "b1",
        1: "b2",
        2: "b3",
        3: "b4",
        5: "b5",
        6: "b7",  # P4_B6 yazısı buraya gitmeli; b6 ileri tuşuna yazıyordu
    },
}

# Reset sırasında daha önce yanlışlıkla yazı gitmiş olabilecek tüm b0-b7 objelerini temizliyoruz.
NEXTION_TEXT_RESET_OBJS = {
    3: ["b0", "b1", "b2", "b3", "b4", "b5", "b6", "b7"],
    4: ["b0", "b1", "b2", "b3", "b4", "b5", "b6", "b7"],
}

def is_valid_user_task(cfg):
    return bool(isinstance(cfg, dict) and cfg.get("action"))

def should_ignore_serial_signal(data):
    if not isinstance(data, str):
        return False
    data = data.strip()
    return (
        not data
        or data.startswith("DEBUG_NEX_SENT:")
        or data.startswith("NEXCMD:")
        or data.startswith("page")
    )

def resolve_nextion_signal(data, buttons_cfg):
    """
    Dokunmatik ekran sinyalinde çeviri yapmaz.
    Nextion hangi sinyali gönderiyorsa görev o anahtarda aranır.
    (2.0: önceki sürümlerden kalan erişilemeyen eski eşleme kodu kaldırıldı.)
    """
    if not isinstance(data, str):
        return data
    return data.strip()

def get_builtin_macros():
    return {
        tr("cat_custom"): {
            tr("act_custom_web"): {"type": "custom_web"},
            tr("act_custom_app"): {"type": "custom_app"},
            tr("act_custom_hotkey"): {"type": "custom_hotkey"}
        },
        tr("cat_text"): {
            tr("act_text_type"): {"type": "type_text"}
        },
        tr("cat_fkeys"): {
            "F13": {"type": "native", "vk": VK_F13}, "F14": {"type": "native", "vk": VK_F14},
            "F15": {"type": "native", "vk": VK_F15}, "F16": {"type": "native", "vk": VK_F16},
            "F17": {"type": "native", "vk": VK_F17}, "F18": {"type": "native", "vk": VK_F18},
            "F19": {"type": "native", "vk": VK_F19}, "F20": {"type": "native", "vk": VK_F20},
            "F21": {"type": "native", "vk": VK_F21}, "F22": {"type": "native", "vk": VK_F22},
            "F23": {"type": "native", "vk": VK_F23}, "F24": {"type": "native", "vk": VK_F24}
        },
        tr("cat_numpad"): {
            "Numpad 0": {"type": "native", "vk": 0x60}, "Numpad 1": {"type": "native", "vk": 0x61},
            "Numpad 2": {"type": "native", "vk": 0x62}, "Numpad 3": {"type": "native", "vk": 0x63},
            "Numpad 4": {"type": "native", "vk": 0x64}, "Numpad 5": {"type": "native", "vk": 0x65},
            "Numpad 6": {"type": "native", "vk": 0x66}, "Numpad 7": {"type": "native", "vk": 0x67},
            "Numpad 8": {"type": "native", "vk": 0x68}, "Numpad 9": {"type": "native", "vk": 0x69},
            "Numpad *": {"type": "native", "vk": 0x6A}, "Numpad +": {"type": "native", "vk": 0x6B},
            "Numpad -": {"type": "native", "vk": 0x6D}, "Numpad .": {"type": "native", "vk": 0x6E},
            "Numpad /": {"type": "native", "vk": 0x6F}
        },
        tr("cat_win"): {
            tr("act_win_max"): {"type": "custom_hotkey", "custom_arg": "win+up"},
            tr("act_win_min"): {"type": "custom_hotkey", "custom_arg": "win+down"},
            tr("act_win_left"): {"type": "custom_hotkey", "custom_arg": "win+left"},
            tr("act_win_right"): {"type": "custom_hotkey", "custom_arg": "win+right"},
            tr("act_win_next"): {"type": "custom_hotkey", "custom_arg": "win+shift+right"},
            tr("act_win_d"): {"type": "custom_hotkey", "custom_arg": "win+d"}
        },
        tr("cat_snip"): {
            tr("act_snip_reg"): {"type": "cmd", "cmd": "start ms-screenclip:"},
            tr("act_snip_full"): {"type": "custom_hotkey", "custom_arg": "win+print screen"},
            tr("act_snip_app"): {"type": "cmd", "cmd": "snippingtool.exe"}
        },
        tr("cat_power"): {
            tr("act_pow_sleep"): {"type": "cmd", "cmd": "rundll32.exe powrprof.dll,SetSuspendState 0,1,0"},
            tr("act_pow_shut"): {"type": "cmd", "cmd": "shutdown /s /t 0"},
            tr("act_pow_res"): {"type": "cmd", "cmd": "shutdown /r /t 0"},
            tr("act_pow_lock"): {"type": "cmd", "cmd": "rundll32.exe user32.dll,LockWorkStation"}
        },
        tr("cat_media"): {
            tr("act_media_pp"): {"type": "native", "vk": VK_MEDIA_PLAY_PAUSE},
            tr("act_media_next"): {"type": "native", "vk": VK_MEDIA_NEXT_TRACK},
            tr("act_media_prev"): {"type": "native", "vk": VK_MEDIA_PREV_TRACK},
            tr("act_media_mute"): {"type": "native", "vk": VK_VOLUME_MUTE}
        },
        tr("cat_vol"): {
            tr("act_vol_up"): {"type": "native", "vk": VK_VOLUME_UP},
            tr("act_vol_down"): {"type": "native", "vk": VK_VOLUME_DOWN},
            tr("act_vol_foc_up"): {"type": "nircmd", "cmd": "changeappvolume focused 0.01"},
            tr("act_vol_foc_down"): {"type": "nircmd", "cmd": "changeappvolume focused -0.01"}
        },
        tr("cat_web"): {
            tr("act_web_yt"): {"type": "web", "cmd": "https://www.youtube.com/@NexHubCo/@NexHubCo"},
            tr("act_web_kick"): {"type": "web", "cmd": "https://kick.com"}
        },
        "👤 Profil": dict(
            [
                ("Sonraki Profile Geç", {"type": "profile", "mode": "next"}),
                ("Önceki Profile Geç", {"type": "profile", "mode": "prev"}),
            ]
            + [
                (f"'{name}' profiline geç", {"type": "profile", "mode": "switch", "custom_arg": name})
                for name in (APP_CONFIG.get("profiles") or {}).keys()
            ]
        ),
        tr("cat_tools"): {
            tr("act_tool_exp"): {"type": "cmd", "cmd": "explorer.exe"},
            tr("act_tool_calc"): {"type": "cmd", "cmd": "calc.exe"},
            tr("act_tool_task"): {"type": "cmd", "cmd": "taskmgr.exe"}
        }
    }

FACTORY_DEFAULT_BUTTONS = {
    # Sayfa 1 - cihazdan gelen gerçek klasik sinyaller
    "NEX:MIC_TOGGLE": {"name": "F13", "action": {"type": "native", "vk": VK_F13}},
    "NEX:DESK_TOGGLE": {"name": "F14", "action": {"type": "native", "vk": VK_F14}},
    "NEX:CAM_TOGGLE": {"name": "F15", "action": {"type": "native", "vk": VK_F15}},
    "NEX:LIVE_TOGGLE": {"name": "F16", "action": {"type": "native", "vk": VK_F16}},
    "NEX:SCENE_1": {"name": "F17", "action": {"type": "native", "vk": VK_F17}},
    "NEX:SCENE_2": {"name": "F18", "action": {"type": "native", "vk": VK_F18}},
    "NEX:SCENE_3": {"name": "F19", "action": {"type": "native", "vk": VK_F19}},

    # Sayfa 2 - cihazdan gelen gerçek klasik sinyaller
    "NEX:MEDIA_PREV": {"name": "Önceki Şarkı", "action": {"type": "native", "vk": VK_MEDIA_PREV_TRACK}},
    "NEX:MEDIA_PP": {"name": "Oynat/Duraklat", "action": {"type": "native", "vk": VK_MEDIA_PLAY_PAUSE}},
    "NEX:MEDIA_NEXT": {"name": "Sonraki Şarkı", "action": {"type": "native", "vk": VK_MEDIA_NEXT_TRACK}},
    "NEX:REC_TOGGLE": {"name": "F20", "action": {"type": "native", "vk": VK_F20}},
    "NEX:OPEN_YT": {"name": "YouTube", "action": {"type": "web", "cmd": "https://www.youtube.com/@NexHubCo"}},
    "NEX:OPEN_KICK": {"name": "Kick", "action": {"type": "web", "cmd": "https://kick.com"}},
}

class NexPluginAPI:
    """
    Eklentilere verilen yardımcı API (eklentide `nex` adıyla erişilir).
      nex.send_hotkey("ctrl+shift+m")   -> NexStudio'nun güvenilir tuş gönderimi (SendInput / USB HID)
      nex.log("mesaj")                  -> Sistem günlüğüne yazar
      nex.get_setting("anahtar", varsayılan) / nex.set_setting("anahtar", değer)
                                         -> config.json > plugin_settings > <eklenti adı>
    """

    def __init__(self, plugin_name):
        self.plugin_name = plugin_name

    def send_hotkey(self, combo):
        keys = [k.strip().lower() for k in str(combo).split("+") if k.strip()]
        vk_list = [VK_MAP[k] for k in keys if k in VK_MAP]
        if len(vk_list) != len(keys):
            raise ValueError(f"Tanınmayan tuş: {combo}")
        if not _send_hotkey_via_device(vk_list):
            send_key_combo(vk_list)

    def log(self, message):
        ui_log(f"🧩 {self.plugin_name}: {message}")

    def get_setting(self, key, default=None):
        return (APP_CONFIG.get("plugin_settings", {}).get(self.plugin_name, {})).get(key, default)

    def set_setting(self, key, value):
        with CONFIG_LOCK:
            APP_CONFIG.setdefault("plugin_settings", {}).setdefault(self.plugin_name, {})[key] = value
        save_config(APP_CONFIG)


def seed_bundled_plugins():
    """
    Kurulumla gelen eklentileri kullanıcının eklenti klasörüne kopyalar.
    (1.x'te paketlenen eklentiler AppData'ya hiç kopyalanmıyordu.)
    Paketteki dosya daha yeniyse eski dosya .bak olarak saklanıp güncellenir.
    """
    bundled_dir = get_resource_path("plugins")
    if not os.path.isdir(bundled_dir) or os.path.abspath(bundled_dir) == os.path.abspath(PLUGINS_DIR):
        return
    for src in glob.glob(os.path.join(bundled_dir, "*.py")):
        dst = os.path.join(PLUGINS_DIR, os.path.basename(src))
        try:
            if not os.path.exists(dst):
                shutil.copy2(src, dst)
            elif os.path.getmtime(src) > os.path.getmtime(dst) + 1:
                with open(src, "rb") as a, open(dst, "rb") as b:
                    if a.read() == b.read():
                        continue
                shutil.copy2(dst, dst + ".bak")
                shutil.copy2(src, dst)
                ui_log(f"🧩 Eklenti güncellendi: {os.path.basename(src)} (eski hali .bak olarak saklandı)")
        except Exception as e:
            write_error_log(f"Eklenti kopyalanamadı ({src}): {e}")


LOADED_PLUGINS = {}
def load_plugins():
    global LOADED_PLUGINS
    LOADED_PLUGINS = {}
    seed_bundled_plugins()
    for file_path in glob.glob(os.path.join(PLUGINS_DIR, "*.py")):
        module_name = os.path.basename(file_path)[:-3]
        try:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            module.nex = NexPluginAPI(module_name)  # modül çalışmadan önce erişilebilir olsun
            spec.loader.exec_module(module)
            if hasattr(module, "PLUGIN_NAME"):
                module.nex.plugin_name = module.PLUGIN_NAME
            if hasattr(module, "PLUGIN_NAME") and hasattr(module, "ACTIONS"):
                LOADED_PLUGINS[module.PLUGIN_NAME] = {"actions": module.ACTIONS, "module": module, "file": file_path}
            else:
                ui_log(f"⚠️ Eklenti atlandı ({os.path.basename(file_path)}): PLUGIN_NAME veya ACTIONS tanımlı değil.")
        except Exception as e:
            write_error_log(f"Eklenti yüklenemedi ({file_path}):\n" + traceback.format_exc())
            ui_log(f"⚠️ Eklenti yüklenemedi ({os.path.basename(file_path)}): {e}")

def get_all_macros():
    all_macros = get_builtin_macros()
    for plugin_name, plugin_data in LOADED_PLUGINS.items():
        all_macros[f"🧩 {plugin_name}"] = plugin_data["actions"]
    return all_macros

PROFILE_KEYS = ["buttons", "encoder", "page_names", "screen_bg"]
DEFAULT_PROFILE_NAME = "Varsayılan"
DEFAULT_MOBILE_PORT = 45729
MOBILE_PORT_RANGE = 20

def find_available_port(start_port=DEFAULT_MOBILE_PORT, count=MOBILE_PORT_RANGE):
    """45729'dan başlayarak gerçekten boş port bulur."""
    for port in range(start_port, start_port + count):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("0.0.0.0", port))
                return port
        except OSError:
            continue
    return None


def snapshot_profile_data(config_data):
    return {
        "buttons": copy.deepcopy(config_data.get("buttons", FACTORY_DEFAULT_BUTTONS.copy())),
        "encoder": copy.deepcopy(config_data.get("encoder", {"turn": "general_volume"})),
        "page_names": copy.deepcopy(config_data.get("page_names", {})),
        "screen_bg": config_data.get("screen_bg", "")
    }

def ensure_profiles(config_data, update_active=False):
    if "profiles" not in config_data or not isinstance(config_data.get("profiles"), dict):
        config_data["profiles"] = {}

    active = config_data.get("active_profile") or DEFAULT_PROFILE_NAME
    config_data["active_profile"] = active

    if not config_data["profiles"]:
        config_data["profiles"][active] = snapshot_profile_data(config_data)

    if active not in config_data["profiles"]:
        config_data["profiles"][active] = snapshot_profile_data(config_data)

    if update_active:
        config_data["profiles"][active] = snapshot_profile_data(config_data)

    return config_data

def apply_active_profile(config_data):
    ensure_profiles(config_data, update_active=False)
    active = config_data.get("active_profile", DEFAULT_PROFILE_NAME)
    pdata = config_data.get("profiles", {}).get(active, {})
    config_data["buttons"] = copy.deepcopy(pdata.get("buttons", FACTORY_DEFAULT_BUTTONS.copy()))
    config_data["encoder"] = copy.deepcopy(pdata.get("encoder", {"turn": "general_volume"}))
    config_data["page_names"] = copy.deepcopy(pdata.get("page_names", {}))
    config_data["screen_bg"] = pdata.get("screen_bg", "")
    return config_data

def load_config():
    global APP_CONFIG
    default_cfg = {
        "language": "tr", "last_port": "", "accent_color": "#3B82F6", 
        "run_in_bg": False, "start_with_win": False, "auto_connect": True, "screen_bg": "", 
        "show_system_log_menu": False,
        "web_auto_start": False, "web_private_log": False, "web_known_only": False,
        "key_send_mode": "auto", "last_port_serial": "", "device_names": {},
        "ui_mode": "modern", "ui_theme": {},
        "known_web_devices": {}, "web_access_history": [],
        "mobile_pin": "", "web_token": "", "logged_in_email": "",
        "encoder": {"turn": "general_volume"},
        "page_names": {},
        "buttons": FACTORY_DEFAULT_BUTTONS.copy(),
        "active_profile": DEFAULT_PROFILE_NAME,
        "profiles": {}
    }
    data = _read_config_file_safely()
    for k, v in data.items():
        if isinstance(v, dict) and isinstance(default_cfg.get(k), dict) and k not in ["buttons", "profiles"]:
            default_cfg[k].update(v)
        else:
            default_cfg[k] = v

    # Eski sürümlerde PIN içeren web adresi config'e yazılıyordu; artık gerek yok.
    default_cfg.pop("mobile_url", None)
    if isinstance(default_cfg.get("web_access_history"), list):
        default_cfg["web_access_history"] = default_cfg["web_access_history"][:WEB_HISTORY_LIMIT]

    if not default_cfg.get("web_token"):
        default_cfg["web_token"] = secrets.token_urlsafe(8)

    if "page_names" in default_cfg:
        for _n in ["1", "2", "3", "4"]:
            if default_cfg["page_names"].get(_n) in [f"Sayfa {_n}", f"Page {_n}"]:
                default_cfg["page_names"].pop(_n, None)

    # Eski tek-config kullanıcılarını profile taşı.
    if not default_cfg.get("profiles"):
        default_cfg["profiles"] = {
            default_cfg.get("active_profile", DEFAULT_PROFILE_NAME): snapshot_profile_data(default_cfg)
        }

    ensure_profiles(default_cfg, update_active=False)
    apply_active_profile(default_cfg)

    APP_CONFIG = default_cfg
    return default_cfg

def save_config(config_data):
    """
    Atomik kayıt: önce geçici dosyaya yazılır, sonra tek hamlede değiştirilir.
    Böylece yazma sırasında uygulama kapanırsa / iki thread aynı anda kaydederse
    config.json bozulmaz. Önceki sağlam kopya config.json.bak olarak tutulur.
    """
    global APP_CONFIG
    with CONFIG_LOCK:
        ensure_profiles(config_data, update_active=True)
        APP_CONFIG = config_data
        tmp_path = CONFIG_FILE + ".tmp"
        try:
            payload = json.dumps(config_data, indent=4, ensure_ascii=False)
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
            if os.path.exists(CONFIG_FILE):
                try:
                    shutil.copy2(CONFIG_FILE, CONFIG_BACKUP_FILE)
                except Exception:
                    pass
            os.replace(tmp_path, CONFIG_FILE)
        except Exception as e:
            write_error_log("Config kaydedilemedi:\n" + traceback.format_exc())
            ui_log(f"⚠️ Ayarlar kaydedilemedi: {e}")


def _read_config_file_safely():
    """config.json okunamazsa yedekten döner; bozuk dosyayı silmez, yanına kopyalar."""
    for path in (CONFIG_FILE, CONFIG_BACKUP_FILE):
        if not os.path.exists(path):
            continue
        try:
            # utf-8-sig: Not Defteri ile düzenlenip BOM eklenmiş dosyalar da okunur.
            with open(path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            if isinstance(data, dict):
                if path == CONFIG_BACKUP_FILE:
                    ui_log("⚠️ config.json okunamadı; son yedekten (config.json.bak) geri yüklendi.")
                return data
        except Exception:
            write_error_log(f"Config okunamadı: {path}\n" + traceback.format_exc())
            if path == CONFIG_FILE:
                try:
                    shutil.copy2(CONFIG_FILE, CONFIG_FILE + f".corrupt-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
                except Exception:
                    pass
    return {}

def format_action_details(action):
    """Kullanıcının atanmış görevin detayını hatırlaması için kısa açıklama üretir."""
    if not isinstance(action, dict):
        return ""

    atype = action.get("type", "")
    browser = action.get("browser", "")
    app_action = action.get("app_action", "")
    custom_arg = str(action.get("custom_arg", "") or "").strip()
    cmd = str(action.get("cmd", "") or "").strip()

    if atype in ["custom_web", "web"]:
        target = custom_arg or cmd
        if target:
            suffix = f" • {browser}" if browser and browser != "default" else ""
            return f"{target}{suffix}"

    if atype == "custom_app":
        if custom_arg:
            mode_map = {"open": "Aç", "close": "Kapat", "force_close": "Zorla kapat"}
            return f"{mode_map.get(app_action, app_action or 'Aç')} • {custom_arg}"

    if atype == "custom_hotkey":
        if custom_arg:
            return custom_arg

    if atype == "type_text":
        if custom_arg:
            preview = custom_arg.replace("\n", " ")
            return preview[:60] + ("..." if len(preview) > 60 else "")

    if atype == "nircmd":
        if cmd:
            return cmd

    if atype == "cmd":
        if cmd:
            return cmd

    if atype == "native":
        vk = action.get("vk")
        if vk:
            return f"VK: {vk}"

    if atype == "profile":
        mode = action.get("mode", "")
        if mode == "switch":
            return f"Profil: {custom_arg}" if custom_arg else "Profil seçilmedi"
        return {"next": "Sonraki profil", "prev": "Önceki profil"}.get(mode, "")

    return ""

def format_assignment_label(cfg):
    if not isinstance(cfg, dict):
        return ""
    name = cfg.get("name", "") or ""
    details = cfg.get("details", "")
    if not details:
        details = format_action_details(cfg.get("action", {}))
    if details:
        return f"{name} — {details}"
    return name

def execute_macro(action, droppable=True):
    """Görevi makro kuyruğuna ekler; arayüzü bekletmez."""
    if not isinstance(action, dict) or not action.get("type"):
        return
    TASK_WORKER.submit(_execute_macro_now, copy.deepcopy(action), droppable=droppable)


def _run_plugin_action(action):
    plugin_name = action.get("plugin_name")
    plugin = LOADED_PLUGINS.get(plugin_name)
    if not plugin:
        ui_log(f"⚠️ Eklenti bulunamadı veya yüklenemedi: {plugin_name}")
        return
    module = plugin["module"]
    if not hasattr(module, "execute"):
        ui_log(f"⚠️ Eklentide execute() fonksiyonu yok: {plugin_name}")
        return

    def _runner():
        started = time.monotonic()
        try:
            module.execute(action.get("function"))
        except Exception as e:
            write_error_log(f"Eklenti hatası ({plugin_name}):\n" + traceback.format_exc())
            ui_log(f"⚠️ Eklenti hatası ({plugin_name}): {e}")
            return
        elapsed = time.monotonic() - started
        if elapsed > 2:
            ui_log(f"🐢 Eklenti yavaş çalıştı ({plugin_name}): {elapsed:.1f} sn")

    # Eklentiler kendi thread'inde çalışır; yavaş/donan bir eklenti diğer tuşları bekletmez.
    threading.Thread(target=_runner, name=f"Plugin-{plugin_name}", daemon=True).start()


def _send_hotkey_via_device(vk_list):
    """Cihaz 'USB klavye' modunu destekliyorsa tuşları gerçek donanım klavyesi gibi gönderir."""
    window = MAIN_WINDOW
    if window is None or not getattr(window, "device_supports_hid", False):
        return False
    mode = APP_CONFIG.get("key_send_mode", "auto")
    if mode == "software":
        return False
    codes = [HID_KEY_CODES.get(vk) for vk in vk_list]
    if not codes or any(c is None for c in codes):
        return False
    thread = getattr(window, "serial_thread", None)
    if not thread or not thread.is_running:
        return False
    thread.send_data("HID:" + ",".join(str(c) for c in codes) + "\n")
    return True


def _execute_macro_now(action):
    try:
        if action["type"] == "native":
            if not _send_hotkey_via_device([action["vk"]]):
                press_key(action["vk"])
        elif action["type"] == "profile":
            run_on_ui(lambda: MAIN_WINDOW and MAIN_WINDOW.handle_profile_action(action))
        elif action["type"] == "cmd":
            subprocess.Popen(action["cmd"], shell=True, creationflags=0x08000000)
        elif action["type"] == "ps":
            subprocess.Popen(["powershell", "-Command", action["cmd"]], creationflags=0x08000000)
        elif action["type"] == "nircmd" and os.path.exists(NIRCMD_PATH):
            subprocess.Popen([NIRCMD_PATH] + action["cmd"].split(), creationflags=0x08000000)
        elif action["type"] in ["web", "custom_web"]:
            browser = action.get("browser", "default")
            url = action.get("cmd", "") if action["type"] == "web" else action.get("custom_arg", "")
            if not url.startswith("http"): url = "https://" + url
            
            if browser == "chrome": subprocess.Popen(f'start "" chrome "{url}"', shell=True, creationflags=0x08000000)
            elif browser == "edge": subprocess.Popen(f'start "" msedge "{url}"', shell=True, creationflags=0x08000000)
            elif browser == "firefox": subprocess.Popen(f'start "" firefox "{url}"', shell=True, creationflags=0x08000000)
            else: webbrowser.open(url)
            
        elif action["type"] == "custom_app":
            app_path = action.get("custom_arg", "")
            app_action = action.get("app_action", "open")
            if app_action == "open":
                os.startfile(app_path)
            elif app_action == "close":
                subprocess.Popen(f'taskkill /IM "{os.path.basename(app_path)}" /T', shell=True, creationflags=0x08000000)
            elif app_action == "force_close":
                subprocess.Popen(f'taskkill /IM "{os.path.basename(app_path)}" /F /T', shell=True, creationflags=0x08000000)
        elif action["type"] == "type_text":
            if HAS_KEYBOARD:
                keyboard.write(action.get("custom_arg", ""), delay=0.01)
        elif action["type"] == "custom_hotkey":
            keys = [k.strip().lower() for k in action.get("custom_arg", "").split("+")]
            vk_list = [VK_MAP[k] for k in keys if k in VK_MAP]
            unknown = [k for k in keys if k and k not in VK_MAP]
            if unknown:
                ui_log(f"⚠️ Tanınmayan tuş adı: {', '.join(unknown)}")
            if vk_list and not _send_hotkey_via_device(vk_list):
                send_key_combo(vk_list)
        elif action["type"] == "plugin":
            _run_plugin_action(action)
    except Exception as e:
        write_error_log("Makro hatası:\n" + traceback.format_exc())
        ui_log(f"⚠️ Makro Hatası: {str(e)}")

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
        if MAIN_WINDOW and hasattr(MAIN_WINDOW, "log_area"):
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
        if not APP_CONFIG.get("web_private_log", False):
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
    known = APP_CONFIG.get("known_web_devices", {}) if isinstance(APP_CONFIG, dict) else {}
    known_data = known.get(device_id, {}) if isinstance(known, dict) else {}
    known_name = known_data.get("name", "") if isinstance(known_data, dict) else ""
    base = f"{info['device_type']} / {info['device_model']} / {info['os_name']} / {info['browser']}"
    if include_known_name and known_name:
        return f"{known_name} | {base}"
    return base


def ensure_known_web_device(ip, user_agent):
    """Başarılı PIN girişinden sonra cihazı tanınan cihaz listesine ekler."""
    try:
        if "known_web_devices" not in APP_CONFIG or not isinstance(APP_CONFIG.get("known_web_devices"), dict):
            APP_CONFIG["known_web_devices"] = {}
        device_id = make_web_device_id(ip, user_agent)
        known = APP_CONFIG["known_web_devices"]
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
        if not APP_CONFIG.get("web_known_only", False):
            return True
        known = APP_CONFIG.get("known_web_devices", {})
        if trusted_device_id and isinstance(known, dict):
            return bool(known.get(trusted_device_id, {}).get("allowed", False))
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
        known = APP_CONFIG.get("known_web_devices", {})
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
        if "known_web_devices" not in APP_CONFIG or not isinstance(APP_CONFIG.get("known_web_devices"), dict):
            APP_CONFIG["known_web_devices"] = {}
        info = parse_web_client_info(user_agent)
        trust_token = secrets.token_urlsafe(32)
        trust_hash = make_web_trust_hash(trust_token)
        device_id = "TRUST-" + hashlib.sha256((trust_hash + "|" + str(user_agent)).encode("utf-8", errors="ignore")).hexdigest()[:16]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        clean_name = str(name or "").strip()
        if not clean_name:
            clean_name = f"{info.get('device_type', 'Cihaz')} - {info.get('browser', 'Tarayıcı')}"
        APP_CONFIG["known_web_devices"][device_id] = {
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
        save_config(APP_CONFIG)
        return trust_token, device_id, APP_CONFIG["known_web_devices"][device_id]
    except Exception:
        return "", "", {}


def update_trusted_web_device_seen(device_id, ip, user_agent):
    try:
        known = APP_CONFIG.get("known_web_devices", {})
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
        APP_CONFIG["known_web_devices"] = known
        save_config(APP_CONFIG)
    except Exception:
        pass


def add_web_history(event_type, ip, user_agent, detail="", device_id_override="", device_name_override=""):
    """Web giriş geçmişine kısa kayıt ekler; listede son 250 kayıt tutulur."""
    try:
        if "web_access_history" not in APP_CONFIG or not isinstance(APP_CONFIG.get("web_access_history"), list):
            APP_CONFIG["web_access_history"] = []
        info = parse_web_client_info(user_agent)
        device_id = device_id_override or make_web_device_id(ip, user_agent)
        known = APP_CONFIG.get("known_web_devices", {}) if isinstance(APP_CONFIG.get("known_web_devices"), dict) else {}
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
        APP_CONFIG["web_access_history"].insert(0, entry)
        APP_CONFIG["web_access_history"] = APP_CONFIG["web_access_history"][:WEB_HISTORY_LIMIT]
        try: save_config(APP_CONFIG)
        except Exception: pass
        try:
            if MAIN_WINDOW and hasattr(MAIN_WINDOW, "refresh_web_security_panel"):
                run_on_ui(MAIN_WINDOW.refresh_web_security_panel)
        except Exception: pass
        return entry
    except Exception:
        return None


def record_web_event(event_type, ip, user_agent, detail="", icon="ℹ️", add_to_history=True, device_id_override=""):
    try:
        known = APP_CONFIG.get("known_web_devices", {}) if isinstance(APP_CONFIG.get("known_web_devices", {}), dict) else {}
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
        accent = APP_CONFIG.get('accent_color', '#3B82F6')
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
            if MAIN_WINDOW and hasattr(MAIN_WINDOW, 'log_area'):
                try:
                    ui_log(f"⚠️ Web arayüz hatası: {e}")
                except Exception:
                    pass
            return self._send_error_page(e)

    def do_POST(self):
        """2.5: NexStudio Web yazma istekleri. PIN 'X-Nex-Pin' başlığında ya da tanınan cihaz çerezi ile."""
        ip, ua = self._client_ip(), self._client_user_agent()
        try:
            token = APP_CONFIG.get("web_token", "")
            path = urllib.parse.urlparse(self.path).path
            prefix = f"/{token}/api2/"
            if not token or not path.startswith(prefix):
                record_web_event("Yetkisiz Web Girişi", ip, ua, f"POST {path}", "🚫")
                return self._send_json({"ok": False, "error": "Yetkisiz"}, status=403)
            trusted = self._trusted_device_id()
            if not trusted:
                if get_pin_block_remaining(ip) > 0:
                    return self._send_json({"ok": False, "error": "Çok fazla hatalı PIN. Biraz bekleyin."}, status=429)
                pin = (self.headers.get("X-Nex-Pin", "") or "").strip().upper()
                correct = APP_CONFIG.get("mobile_pin", "").strip().upper()
                if not pin or pin != correct:
                    register_pin_failure(ip)
                    record_web_event("Hatalı PIN denemesi", ip, ua, "Yanlış PIN girildi", "🔐")
                    return self._send_json({"ok": False, "error": "PIN hatalı"}, status=401)
            if not is_known_web_device_allowed(ip, ua, trusted):
                return self._send_json({"ok": False, "error": "Bu cihaz tanınan cihazlar listesinde değil."}, status=403)
            body = read_json_body(self, limit=8 * 1024 * 1024)
            status, payload = AppApi.dispatch("POST", path[len(prefix):], body, remote=True)
            return self._send_json(payload, status=status)
        except Exception as e:
            write_error_log("Web POST hatası:\n" + traceback.format_exc())
            return self._send_json({"ok": False, "error": str(e)}, status=500)

    def _do_GET_safe(self):
        token = APP_CONFIG.get("web_token", "")
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
        correct_pin = APP_CONFIG.get("mobile_pin", "").strip().upper()
        trusted_device_id = self._trusted_device_id()
        trusted_auth = bool(trusted_device_id)

        if not trusted_auth:
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
                return send_icon_file(self, parsed_path.split("/icons/", 1)[1])
            query = {k: v[0] for k, v in params.items() if k not in ("pin", "trust")}
            status, payload = AppApi.dispatch("GET", parsed_path.split("/api2/", 1)[1], query, remote=True)
            return self._send_json(payload, status=status)

        if self.path.startswith(f'/{token}/exec'):
            sig = params.get('sig', [''])[0]
            if sig in APP_CONFIG.get("buttons", {}):
                action = APP_CONFIG["buttons"][sig].get("action")
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
                
                if "buttons" not in APP_CONFIG:
                    APP_CONFIG["buttons"] = {}
                APP_CONFIG["buttons"][sig] = {"name": act, "action": action_data}
                if sig.startswith("NEX:P3_") or sig.startswith("NEX:P4_"):
                    APP_CONFIG["buttons"][sig]["btn_text"] = btn_text
                save_config(APP_CONFIG)
                if MAIN_WINDOW:
                    run_on_ui(lambda: MAIN_WINDOW.refresh_screen_buttons())
                    if sig.startswith("NEX:P3_") or sig.startswith("NEX:P4_"):
                        run_on_ui(lambda: MAIN_WINDOW.sync_nextion_texts())
                
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
            return
            
        if self.path.startswith(f'/{token}/api/save_page_name'):
            page = params.get('page', [''])[0]
            name = params.get('name', [''])[0]
            if "page_names" not in APP_CONFIG:
                APP_CONFIG["page_names"] = {}
            APP_CONFIG["page_names"][page] = name
            save_config(APP_CONFIG)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
            return

        if self.path.startswith(f'/{token}/api/save_accent'):
            color = params.get('color', [''])[0].strip()
            if re.match(r'^#[0-9A-Fa-f]{6}$', color):
                APP_CONFIG["accent_color"] = color.upper()
                save_config(APP_CONFIG)
                if MAIN_WINDOW:
                    try:
                        MAIN_WINDOW.config["accent_color"] = color.upper()
                        run_on_ui(MAIN_WINDOW.apply_theme)
                    except Exception:
                        pass
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
            return

        if self.path.startswith(f'/{token}/api/encoder'):
            mode = params.get('mode', [''])[0]
            if "encoder" not in APP_CONFIG:
                APP_CONFIG["encoder"] = {}
            if mode:
                APP_CONFIG["encoder"]["turn"] = mode
                save_config(APP_CONFIG)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
            return

        if self.path.startswith(f'/{token}/api/volume'):
            direction = params.get('dir', [''])[0]
            mode = params.get('mode', [APP_CONFIG.get("encoder", {}).get("turn", "general_volume")])[0]
            try:
                steps = int(params.get('steps', ['1'])[0])
            except:
                steps = 1
            steps = max(1, min(20, abs(steps)))
            delta = (0.01 * steps) if direction == "up" else (-0.01 * steps)
            try:
                if MAIN_WINDOW:
                    if mode in ["general_volume", "Genel Ses Seviyesi", "General Volume", ""]:
                        TASK_WORKER.submit(MAIN_WINDOW.change_master_volume, delta)
                    elif mode in ["brightness", "Ekran Parlaklığı", "Screen Brightness"]:
                        brightness_delta = max(-20, min(20, steps if direction == "up" else -steps))
                        execute_macro({"type": "nircmd", "cmd": f"changebrightness {brightness_delta}"})
                    else:
                        TASK_WORKER.submit(MAIN_WINDOW.change_app_volume, mode, delta)
            except Exception as e:
                if MAIN_WINDOW and hasattr(MAIN_WINDOW, "log_area"):
                    ui_log(f"Web volume error: {e}")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
            return

        if self.path.startswith(f'/{token}/api/audio_apps'):
            try:
                apps = MAIN_WINDOW.get_audio_mixer_apps() if MAIN_WINDOW else []
            except Exception:
                apps = []
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(apps, ensure_ascii=False).encode('utf-8'))
            return


        if not is_known_web_device_allowed(self._client_ip(), self._client_user_agent(), trusted_device_id):
            record_web_event("Tanınmayan cihaz engellendi", self._client_ip(), self._client_user_agent(), "Sadece tanınan cihazlar modu açık", "⛔")
            return self._send_plain_text("Bu cihaz tanınan cihazlar listesinde olmadığı için Web Kontrolü kullanılamaz.", status=403)

        self._log_web_login_once("Tanınan cihaz" if trusted_auth else "PIN girişi", trusted_device_id)
        # 2.5: Telefonda da yeni arayüz (NexStudio Web). Eski web arayüzü: adresin sonuna ?classic=1
        if params.get("classic", [""])[0] != "1" and os.path.exists(os.path.join(WEB_UI_DIR, "app.html")):
            auth_q = "" if trusted_auth else "pin=" + urllib.parse.quote(pin)
            html = read_app_html(f"/{token}/api2", True, auth_q)
            return send_bytes(self, html.encode("utf-8"), "text/html; charset=utf-8")
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        
        macros_json = json.dumps(get_all_macros(), ensure_ascii=False)
        buttons_json = json.dumps(get_physical_buttons(), ensure_ascii=False)
        translations_json = json.dumps(TRANSLATIONS, ensure_ascii=False)
        page_names_json = json.dumps(APP_CONFIG.get("page_names", {}), ensure_ascii=False)
        encoder_json = json.dumps(APP_CONFIG.get("encoder", {}), ensure_ascii=False)
        touch_map_json = json.dumps(TOUCH_UI_SLOT_TO_SIGNAL, ensure_ascii=False)
        device_connected_json = json.dumps(bool(MAIN_WINDOW and getattr(MAIN_WINDOW, "serial_thread", None) and MAIN_WINDOW.serial_thread.is_running))
        
        try:
            audio_apps_json = json.dumps(MAIN_WINDOW.get_audio_mixer_apps() if MAIN_WINDOW else [], ensure_ascii=False)
        except Exception:
            audio_apps_json = json.dumps([], ensure_ascii=False)
        
        user_agent = self.headers.get("User-Agent", "")
        is_mobile_client = bool(re.search(r"Android|iPhone|iPad|iPod|Mobile|Windows Phone", user_agent, re.I))
        logo_html = get_nexstudio_logo_html()
        known_for_page = APP_CONFIG.get("known_web_devices", {}) if isinstance(APP_CONFIG.get("known_web_devices", {}), dict) else {}
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
                    --accent: {APP_CONFIG.get('accent_color', '#3B82F6')};
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
                <input type="text" id="web-accent-color" value="{APP_CONFIG.get('accent_color', '#3B82F6')}" placeholder="#3B82F6" maxlength="7">
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
            let currentConfig = {json.dumps(APP_CONFIG.get("buttons", {}), ensure_ascii=False)};
            const touchMap = {touch_map_json};
            const deviceConnected = {device_connected_json};
            let currentLang = localStorage.getItem('nex_lang') || '{APP_CONFIG.get("language", "tr")}';
            
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
            let selectedAccent = '{APP_CONFIG.get('accent_color', '#3B82F6')}';

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
                        --accent: {APP_CONFIG.get('accent_color', '#3B82F6')};
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
                                <input type="text" id="d-accent-color" value="{APP_CONFIG.get('accent_color', '#3B82F6')}" placeholder="#3B82F6" maxlength="7">
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
                    let currentConfig = {json.dumps(APP_CONFIG.get("buttons", {}), ensure_ascii=False)};
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
                    let desktopSelectedAccent = '{APP_CONFIG.get('accent_color', '#3B82F6')}';

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
    allow_reuse_address = True
    daemon_threads = True


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


# =========================================================
# 6. SERİ PORT HABERLEŞMESİ (ARDUINO)
# =========================================================
class SerialThread(QThread):
    """
    Arduino ile seri haberleşme.
    2.0: kendi satır tamponu (yarım satır gelmez), kopma algılama, thread-güvenli yazma,
    port kapatma işlemini okuma thread'inin kendisi yapar (yarış durumu yok).
    """
    data_received = pyqtSignal(str)
    connection_error = pyqtSignal(str)
    connected = pyqtSignal(str)

    def __init__(self, port):
        super().__init__()
        self.port = port
        self.serial_conn = None
        self.is_running = True
        self._stop_requested = False
        self._write_lock = threading.Lock()
        self.last_rx = time.monotonic()

    def run(self):
        buf = b""
        try:
            self.serial_conn = serial.Serial(self.port, 9600, timeout=0.05, write_timeout=1)
            try:
                self.serial_conn.dtr = True  # Pro Micro (32U4) USB-CDC, DTR olmadan veri göndermeyebilir.
            except Exception:
                pass
            self.last_rx = time.monotonic()
            self.connected.emit(self.port)
            self.send_data("HELLO\n")  # 2.0 firmware kimlik bilgisi döner; eski firmware yok sayar.
            while not self._stop_requested:
                chunk = self.serial_conn.read(self.serial_conn.in_waiting or 1)
                if not chunk:
                    continue
                self.last_rx = time.monotonic()
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    text = line.decode("utf-8", errors="ignore").strip()
                    if text:
                        self.data_received.emit(text)
                if len(buf) > 1024:
                    buf = b""
        except Exception as e:
            if not self._stop_requested:
                self.connection_error.emit(str(e))
        finally:
            self.is_running = False
            try:
                if self.serial_conn and self.serial_conn.is_open:
                    self.serial_conn.close()
            except Exception:
                pass

    def send_data(self, data_str):
        conn = self.serial_conn
        if not conn or not conn.is_open:
            return False
        with self._write_lock:
            try:
                conn.write(data_str.encode("iso-8859-9", errors="replace"))
                return True
            except Exception as e:
                write_error_log(f"Seri yazma hatası ({self.port}): {e}")
                return False

    def stop(self):
        self._stop_requested = True


# =========================================================
# 7. ARAYÜZ (UI) VE ANA UYGULAMA SINIFI
# =========================================================
def get_stylesheet(accent_color):
    return f"""
    * {{
        font-family: 'Segoe UI';
        outline: none;
    }}

    QMainWindow, QWidget {{
        background-color: #070B14;
        color: #F8FAFC;
        font-size: 14px;
    }}

    QLabel {{
        background: transparent;
    }}

    QWidget#AppRoot, QWidget#ContentRoot, QStackedWidget#MainStack {{
        background-color: #070B14;
    }}

    QWidget#MainPage, QWidget#PageSurface {{
        background-color: #070B14;
    }}

    QWidget#SideRail {{
        background-color: #0B1220;
        border: 1px solid #1C2638;
        border-radius: 30px;
    }}

    QLabel#BrandTitle {{
        color: #FFFFFF;
        font-size: 25px;
        font-weight: 900;
        letter-spacing: 1px;
    }}

    QLabel#BrandSub {{
        color: #748298;
        font-size: 12px;
        font-weight: 700;
    }}

    QLabel#PageTitle {{
        color: #FFFFFF;
        font-size: 28px;
        font-weight: 900;
    }}

    QLabel#PageSubtitle {{
        color: #94A3B8;
        font-size: 13px;
        font-weight: 600;
    }}

    QLabel#SectionTitle {{
        color: #FFFFFF;
        font-size: 17px;
        font-weight: 900;
        background: transparent;
    }}

    QLabel#Muted {{
        color: #94A3B8;
        font-size: 12px;
        font-weight: 600;
        background: transparent;
    }}

    QLabel#StatusPill {{
        color: #94A3B8;
        background-color: #111827;
        border: 1px solid #263244;
        border-radius: 16px;
        padding: 8px 12px;
        font-size: 12px;
        font-weight: 800;
    }}

    QWidget#GlassCard, QFrame#GlassCard {{
        background-color: #0E1625;
        border: 1px solid #1E2A3D;
        border-radius: 28px;
    }}

    QWidget#Topbar {{
        background-color: #0E1625;
        border: 1px solid #1E2A3D;
        border-radius: 24px;
    }}

    QWidget#HeroCard {{
        background-color: #101A2D;
        border: 1px solid #26364F;
        border-radius: 28px;
    }}

    QPushButton {{
        background-color: #182235;
        color: #F8FAFC;
        border: 1px solid #28364D;
        border-radius: 14px;
        padding: 11px 14px;
        font-weight: 800;
    }}

    QPushButton:hover {{
        background-color: {accent_color};
        border-color: {accent_color};
        color: #FFFFFF;
    }}

    QPushButton:pressed {{
        background-color: #0F172A;
        padding-top: 12px;
        padding-bottom: 10px;
    }}

    QPushButton#NavBtn {{
        background-color: transparent;
        color: #8B98AA;
        border: none;
        border-radius: 18px;
        padding: 14px 12px;
        font-size: 14px;
        text-align: left;
        font-weight: 900;
    }}

    QPushButton#NavBtn:hover {{
        background-color: #121D2F;
        color: #FFFFFF;
    }}

    QPushButton#NavBtn:checked {{
        background-color: {accent_color};
        color: #FFFFFF;
    }}

    QPushButton#IconBtn {{
        background-color: #111827;
        color: #CBD5E1;
        border: 1px solid #263244;
        border-radius: 16px;
        min-width: 46px;
        min-height: 44px;
        font-size: 18px;
        font-weight: 800;
        padding: 0;
    }}

    QPushButton#IconBtn:hover {{
        color: #FFFFFF;
        background-color: {accent_color};
        border-color: {accent_color};
    }}

    QPushButton#SettingsTopBtn {{
        background-color: #111827;
        color: #CBD5E1;
        border: 1px solid #263244;
        border-radius: 16px;
        min-height: 44px;
        padding-left: 16px;
        padding-right: 16px;
        font-size: 13px;
        font-weight: 900;
    }}

    QPushButton#SettingsTopBtn:hover {{
        background-color: {accent_color};
        color: #FFFFFF;
        border-color: {accent_color};
    }}

    QPushButton#ConnectBtn {{
        background-color: #10B981;
        color: white;
        border-color: #10B981;
        padding-left: 18px;
        padding-right: 18px;
    }}

    QPushButton#FloatingSettingsBtn {{
        background-color: #0F172A;
        color: #FFFFFF;
        border: 1px solid #2A3C59;
        border-radius: 23px;
        padding-left: 14px;
        padding-right: 14px;
        font-size: 14px;
        font-weight: 900;
        text-align: left;
    }}

    QPushButton#FloatingSettingsBtn:hover {{
        background-color: #162238;
        border-color: {accent_color};
    }}

    QPushButton#DisconnectBtn {{
        background-color: #EF4444;
        color: white;
        border-color: #EF4444;
        padding-left: 18px;
        padding-right: 18px;
    }}

    QPushButton#SaveBtn {{
        background-color: {accent_color};
        color: #FFFFFF;
        border: 1px solid {accent_color};
        border-radius: 18px;
        padding: 15px 20px;
        font-size: 15px;
        font-weight: 900;
    }}

    QPushButton#DangerBtn {{
        background-color: #EF4444;
        color: #FFFFFF;
        border-color: #EF4444;
    }}

    QListWidget {{
        background-color: #0B1220;
        border: 1px solid #1E2A3D;
        border-radius: 22px;
        padding: 10px;
        outline: none;
    }}

    QListWidget::item {{
        padding: 15px 14px;
        margin: 4px;
        border-radius: 14px;
        color: #CBD5E1;
        font-weight: 800;
    }}

    QListWidget::item:hover {{
        background-color: {accent_color};
        color: #FFFFFF;
    }}

    QListWidget::item:selected {{
        background-color: {accent_color};
        color: #FFFFFF;
        border: 1px solid rgba(255,255,255,0.30);
    }}

    QGroupBox {{
        background-color: #0B1220;
        border: 1px solid #1E2A3D;
        border-radius: 22px;
        margin-top: 14px;
        padding: 20px 16px 16px 16px;
        font-weight: 900;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 18px;
        top: 5px;
        padding: 0 8px;
        color: #FFFFFF;
        background-color: #0B1220;
    }}

    QComboBox, QLineEdit {{
        background-color: #080D16;
        color: #F8FAFC;
        border: 1px solid #27354A;
        border-radius: 14px;
        padding: 11px 12px;
        font-weight: 700;
        selection-background-color: {accent_color};
    }}

    QComboBox:hover, QLineEdit:hover {{
        border-color: {accent_color};
        background-color: #111B2E;
    }}

    QComboBox:focus, QLineEdit:focus {{
        border-color: {accent_color};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 28px;
    }}

    QComboBox QAbstractItemView {{
        background-color: #0B1220;
        color: #F8FAFC;
        border: 1px solid #27354A;
        selection-background-color: {accent_color};
        padding: 6px;
    }}

    QTextEdit {{
        background-color: #050914;
        color: #22C55E;
        border: 1px solid #1E2A3D;
        border-radius: 22px;
        font-family: 'Consolas';
        padding: 16px;
    }}

    QScrollArea {{
        background: transparent;
        border: none;
    }}


    QScrollBar:vertical {{
        background-color: #0B1220;
        width: 12px;
        margin: 8px 2px 8px 2px;
        border-radius: 6px;
    }}

    QScrollBar::handle:vertical {{
        background-color: #334155;
        min-height: 42px;
        border-radius: 6px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {accent_color};
    }}

    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0px;
        background: transparent;
        border: none;
    }}

    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {{
        background: transparent;
    }}

    QScrollBar:horizontal {{
        background-color: #0B1220;
        height: 12px;
        margin: 2px 8px 2px 8px;
        border-radius: 6px;
    }}

    QScrollBar::handle:horizontal {{
        background-color: #334155;
        min-width: 42px;
        border-radius: 6px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background-color: {accent_color};
    }}

    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {{
        width: 0px;
        background: transparent;
        border: none;
    }}

    QScrollBar::add-page:horizontal,
    QScrollBar::sub-page:horizontal {{
        background: transparent;
    }}


    QSplitter::handle {{
        background-color: transparent;
        width: 12px;
        height: 12px;
    }}

    QFrame#ScreenFrame {{
        border-radius: 28px;
        border: 8px solid #070B14;
    }}

    QPushButton#ScreenBtn {{
        background-color: rgba(8, 13, 22, 0.88);
        border: 1px solid rgba(148, 163, 184, 0.28);
        border-radius: 20px;
        color: #FFFFFF;
        font-weight: 900;
        font-size: 13px;
        min-height: 78px;
    }}

    QPushButton#ScreenBtn:hover {{
        background-color: {accent_color};
        border-color: {accent_color};
        color: #FFFFFF;
    }}

    QPushButton#ScreenBtn:disabled {{
        background-color: #0F172A;
        border: 1px solid #334155;
        color: #64748B;
    }}
    """


class ColorNavButton(QFrame):
    clicked = pyqtSignal()

    def __init__(self, badge_text, badge_color, label, parent=None):
        super().__init__(parent)
        self._checked = False
        self.badge_color = badge_color
        self.setObjectName("ColorNavButton")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setMinimumHeight(56)
        self.setMaximumHeight(56)
        self.nav_anim_min = QPropertyAnimation(self, b"minimumHeight")
        self.nav_anim_max = QPropertyAnimation(self, b"maximumHeight")
        for anim in (self.nav_anim_min, self.nav_anim_max):
            anim.setDuration(220)
            anim.setEasingCurve(QEasingCurve.OutCubic)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        self.badge = QLabel(badge_text)
        self.badge.setFixedSize(32, 32)
        self.badge.setAlignment(Qt.AlignCenter)
        self.badge.setStyleSheet(
            f"background-color: {badge_color}; color: white; border-radius: 11px; font-size: 15px; font-weight: 900;"
        )

        self.label = QLabel(label)
        self.label.setStyleSheet("color: #A9B7CA; font-size: 14px; font-weight: 800; background: transparent;")

        layout.addWidget(self.badge)
        layout.addWidget(self.label)
        layout.addStretch()
        self.refresh_style()

    def setChecked(self, checked):
        self._checked = checked
        self.refresh_style()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

    def enterEvent(self, event):
        if not self._checked:
            self.animate_height(62)
            self.setStyleSheet(
                f"QFrame#ColorNavButton {{ background-color: {self.badge_color}; border: 1px solid {self.badge_color}; border-radius: 16px; }}"
            )
            self.label.setStyleSheet("color: #FFFFFF; font-size: 14px; font-weight: 900; background: transparent;")
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self._checked:
            self.animate_height(56)
            self.refresh_style()
        super().leaveEvent(event)

    def animate_height(self, target):
        for anim, prop_getter in ((self.nav_anim_min, self.minimumHeight), (self.nav_anim_max, self.maximumHeight)):
            anim.stop()
            anim.setStartValue(prop_getter())
            anim.setEndValue(target)
            anim.start()

    def refresh_style(self):
        if self._checked:
            self.animate_height(62)
            self.setStyleSheet(
                f"QFrame#ColorNavButton {{ background-color: {self.badge_color}; border: 1px solid {self.badge_color}; border-radius: 16px; }}"
            )
            self.label.setStyleSheet("color: #FFFFFF; font-size: 14px; font-weight: 900; background: transparent;")
        else:
            self.animate_height(56)
            self.setStyleSheet(
                "QFrame#ColorNavButton { background-color: transparent; border: 1px solid transparent; border-radius: 16px; }"
            )
            self.label.setStyleSheet("color: #A9B7CA; font-size: 14px; font-weight: 800; background: transparent;")




class AnimatedButton(QPushButton):
    def __init__(self, text="", parent=None, accent=None):
        super().__init__(text, parent)
        self.accent = accent or "#3B82F6"
        self._base_min_height = 0
        self.anim_min = QPropertyAnimation(self, b"minimumHeight")
        self.anim_max = QPropertyAnimation(self, b"maximumHeight")
        for anim in (self.anim_min, self.anim_max):
            anim.setDuration(220)
            anim.setEasingCurve(QEasingCurve.OutCubic)
        self.apply_default_style()

    def accent_color(self):
        try:
            return self.accent() if callable(self.accent) else self.accent
        except Exception:
            return "#3B82F6"

    def apply_default_style(self):
        accent = self.accent_color()
        self.setStyleSheet(
            f"background-color: #111827; color: #FFFFFF; border: 1px solid {accent}; border-radius: 18px; "
            "padding: 14px 18px; font-size: 15px; font-weight: 800;"
        )

    def apply_hover_style(self):
        accent = self.accent_color()
        self.setStyleSheet(
            f"background-color: {accent}; color: #FFFFFF; border: 1px solid {accent}; border-radius: 18px; "
            "padding: 14px 18px; font-size: 15px; font-weight: 800;"
        )

    def setHoverHeights(self, base_height, grow_by=6):
        self._base_min_height = base_height
        self._grow_by = grow_by
        self.setMinimumHeight(base_height)
        self.setMaximumHeight(base_height + 24)

    def enterEvent(self, event):
        self.apply_hover_style()
        if self._base_min_height:
            for anim, getter in ((self.anim_min, self.minimumHeight), (self.anim_max, self.maximumHeight)):
                anim.stop()
                anim.setStartValue(getter())
                anim.setEndValue(self._base_min_height + self._grow_by)
                anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.apply_default_style()
        if self._base_min_height:
            for anim, getter in ((self.anim_min, self.minimumHeight), (self.anim_max, self.maximumHeight)):
                anim.stop()
                anim.setStartValue(getter())
                anim.setEndValue(self._base_min_height)
                anim.start()
        super().leaveEvent(event)


class HoverScaleFrame(QFrame):
    clicked = pyqtSignal()

    def __init__(self, parent=None, grow_by=10):
        super().__init__(parent)
        self._base_min_height = 0
        self._grow_by = grow_by
        self.setMouseTracking(True)
        self.anim_min = QPropertyAnimation(self, b"minimumHeight")
        self.anim_max = QPropertyAnimation(self, b"maximumHeight")
        for anim in (self.anim_min, self.anim_max):
            anim.setDuration(240)
            anim.setEasingCurve(QEasingCurve.OutCubic)

    def setHoverHeights(self, base_height, grow_by=None):
        self._base_min_height = base_height
        if grow_by is not None:
            self._grow_by = grow_by
        self.setMinimumHeight(base_height)
        self.setMaximumHeight(base_height + 80)

    def enterEvent(self, event):
        if self._base_min_height:
            self.anim_min.stop()
            self.anim_min.setStartValue(self.minimumHeight())
            self.anim_min.setEndValue(self._base_min_height + self._grow_by)
            self.anim_min.start()
        self.raise_()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._base_min_height:
            self.anim_min.stop()
            self.anim_min.setStartValue(self.minimumHeight())
            self.anim_min.setEndValue(self._base_min_height)
            self.anim_min.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class ColorActionCard(HoverScaleFrame):
    clicked = pyqtSignal()

    def __init__(self, badge_text, badge_color, title, desc, parent=None):
        super().__init__(parent, grow_by=10)
        self.accent_color = badge_color
        self.setObjectName("ColorActionCard")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setHoverHeights(150, 10)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        top = QHBoxLayout()
        badge = QLabel(badge_text)
        badge.setFixedSize(40, 40)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(
            f"background-color: {badge_color}; color: white; border-radius: 13px; font-size: 18px; font-weight: 900;"
        )
        top.addWidget(badge)
        top.addStretch()
        layout.addLayout(top)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: white; font-size: 18px; font-weight: 900; background: transparent;")
        lbl_desc = QLabel(desc)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #9FB0C7; font-size: 12px; font-weight: 700; background: transparent;")
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_desc)
        layout.addStretch()

        self.apply_card_style(False)

    def apply_card_style(self, hovered=False):
        if hovered:
            self.setStyleSheet(
                f"QFrame#ColorActionCard {{ background-color: {self.accent_color}; border: 1px solid {self.accent_color}; border-radius: 24px; }}"
            )
        else:
            self.setStyleSheet(
                "QFrame#ColorActionCard { background-color: #101A2D; border: 1px solid #26364F; border-radius: 24px; }"
            )

    def enterEvent(self, event):
        self.apply_card_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.apply_card_style(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class ToastLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ToastLabel")
        self.setAlignment(Qt.AlignCenter)
        self.setVisible(False)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)
        self.effect.setOpacity(0.0)
        self.fade = QPropertyAnimation(self.effect, b"opacity")
        self.fade.setDuration(180)
        self.fade.setEasingCurve(QEasingCurve.OutCubic)
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.fade_out)
        self.setStyleSheet(
            "QLabel#ToastLabel { background-color: #0B1220; color: #FFFFFF; "
            "border: 1px solid #10B981; border-radius: 18px; "
            "padding: 10px 18px; font-size: 13px; font-weight: 900; }"
        )

    def show_message(self, text, duration=1500):
        self.setText(text)
        self.setMinimumWidth(190)
        self.adjustSize()
        self.setVisible(True)
        self.raise_()
        self.fade.stop()
        self.fade.setStartValue(self.effect.opacity())
        self.fade.setEndValue(1.0)
        self.fade.start()
        self.hide_timer.start(duration)

    def fade_out(self):
        self.fade.stop()
        self.fade.setStartValue(self.effect.opacity())
        self.fade.setEndValue(0.0)
        try:
            self.fade.finished.disconnect(self._hide_after_fade)
        except Exception:
            pass
        self.fade.finished.connect(self._hide_after_fade)
        self.fade.start()

    def _hide_after_fade(self):
        try:
            self.fade.finished.disconnect(self._hide_after_fade)
        except Exception:
            pass
        self.setVisible(False)


class FloatingSettingsButton(QPushButton):
    def __init__(self, label, parent=None):
        super().__init__(parent)
        self.full_label = label
        self._gear_rotation = 0.0
        self._hovered = False
        self.button_width = 128
        self.button_height = 46
        self._anchor_margin = 24
        self.setObjectName("FloatingSettingsBtn")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedSize(self.button_width, self.button_height)
        self.setMouseTracking(True)

        self.rotation_anim = QPropertyAnimation(self, b"gearRotation")
        self.rotation_anim.setDuration(420)
        self.rotation_anim.setEasingCurve(QEasingCurve.OutCubic)

    @pyqtProperty(float)
    def gearRotation(self):
        return self._gear_rotation

    @gearRotation.setter
    def gearRotation(self, value):
        self._gear_rotation = value
        self.update()

    def set_anchor_position(self, parent_width, parent_height):
        x = parent_width - self.button_width - self._anchor_margin
        y = parent_height - self.button_height - self._anchor_margin
        self.move(max(0, x), max(0, y))
        self.raise_()

    def enterEvent(self, event):
        self._hovered = True
        self.rotation_anim.stop()
        self.rotation_anim.setStartValue(self._gear_rotation)
        self.rotation_anim.setEndValue(self._gear_rotation + 120.0)
        self.rotation_anim.start()
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.rotation_anim.stop()
        self.rotation_anim.setStartValue(self._gear_rotation)
        self.rotation_anim.setEndValue(0.0)
        self.rotation_anim.start()
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(0, 0, -1, -1)

        bg = QColor("#162238") if self._hovered else QColor("#0F172A")
        border = QColor(self.config.get("accent_color", "#3B82F6")) if self._hovered else QColor("#2A3C59")

        painter.setPen(QPen(border, 1))
        painter.setBrush(bg)
        painter.drawRoundedRect(rect, 23, 23)

        painter.save()
        painter.translate(24, self.height() / 2)
        painter.rotate(self._gear_rotation)
        icon_font = QFont("Segoe UI Symbol", 15, QFont.Bold)
        painter.setFont(icon_font)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(-10, 8, "⚙")
        painter.restore()

        painter.setPen(QColor("#FFFFFF"))
        txt_font = QFont("Segoe UI", 10, QFont.Bold)
        painter.setFont(txt_font)
        text_rect = rect.adjusted(46, 0, -12, 0)
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self.full_label)


class ChangelogHoverCard(QFrame):
    def __init__(self, title, hint_text, entries, parent=None):
        super().__init__(parent)
        self._hovered = False
        self.entries = entries
        self.setObjectName("ChangelogHoverCard")
        self.setFixedWidth(360)
        self.setMinimumHeight(210)
        self.setMaximumHeight(210)
        self.anim = QPropertyAnimation(self, b"maximumHeight")
        self.anim.setDuration(280)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("SectionTitle")
        layout.addWidget(self.lbl_title)

        self.lbl_hint = QLabel(hint_text)
        self.lbl_hint.setObjectName("Muted")
        self.lbl_hint.setWordWrap(True)
        layout.addWidget(self.lbl_hint)

        self.lbl_body = QLabel()
        self.lbl_body.setWordWrap(True)
        self.lbl_body.setTextFormat(Qt.RichText)
        self.lbl_body.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.lbl_body.setStyleSheet("color: #E5ECF6; font-size: 13px; line-height: 1.5; background: transparent;")
        # 2.0: Tüm sürüm geçmişi kaydırılarak okunur.
        self.body_scroll = QScrollArea()
        self.body_scroll.setWidgetResizable(True)
        self.body_scroll.setFrameShape(QFrame.NoFrame)
        self.body_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.body_scroll.setStyleSheet("QScrollArea { background: transparent; } QScrollArea > QWidget > QWidget { background: transparent; }")
        self.body_scroll.setWidget(self.lbl_body)
        layout.addWidget(self.body_scroll, 1)
        self.set_entries(entries)
        self.refresh_style()

    def set_entries(self, entries):
        """entries: [("Sürüm", "Tarih", [maddeler]), ...]  (eski [(tarih, metin)] biçimi de desteklenir)"""
        self.entries = entries
        html_parts = []
        for entry in entries:
            if len(entry) == 3:
                version, date_text, items = entry
                html_parts.append(
                    f'<div style="margin-top:12px; color:#F8FAFC; font-size:14px; font-weight:900;">{html_escape(version)}'
                    f'<span style="color:#A7B8D0; font-size:11px; font-weight:700;">  ·  {html_escape(date_text)}</span></div>'
                )
                for item in items:
                    html_parts.append(f'<div style="margin-top:4px; color:#E5ECF6; font-size:12px;">• {html_escape(item)}</div>')
            else:
                date_text, desc = entry
                html_parts.append(
                    f'<div style="margin-top:8px; color:#A7B8D0; font-size:11px; font-weight:700;">{html_escape(date_text)}</div>'
                    f'<div style="margin-top:4px; color:#F8FAFC; font-size:13px;">• {html_escape(desc)}</div>'
                )
        self.lbl_body.setText("".join(html_parts))

    def refresh_style(self):
        if self._hovered:
            self.setStyleSheet(
                "QFrame#ChangelogHoverCard { background-color: #101A2D; border: 1px solid "
                + str(APP_CONFIG.get("accent_color", "#3B82F6")) + "; border-radius: 24px; }"
            )
        else:
            self.setStyleSheet(
                "QFrame#ChangelogHoverCard { background-color: #101A2D; border: 1px solid #26364F; border-radius: 24px; }"
            )

    def enterEvent(self, event):
        self._hovered = True
        self.raise_()
        self.anim.stop()
        self.anim.setStartValue(self.maximumHeight())
        self.anim.setEndValue(390)
        self.anim.start()
        self.refresh_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.anim.stop()
        self.anim.setStartValue(self.maximumHeight())
        self.anim.setEndValue(210)
        self.anim.start()
        self.refresh_style()
        super().leaveEvent(event)


class NexHubApp(QMainWindow):
    def __init__(self):
        super().__init__()
        global MAIN_WINDOW
        MAIN_WINDOW = self
        
        self.config = load_config()
        cleanup_old_log_files(7)
        load_locales()
        load_plugins()
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
        if hasattr(self, "log_area"):
            self.log_area.document().setMaximumBlockCount(1500)
        flush_pending_ui_logs()
        ui_log(f"NexStudio {APP_VERSION} başlatıldı" + (" (yönetici)" if is_process_elevated() else ""))
        self.apply_startup_setting()
        QTimer.singleShot(900, self.auto_connect_device)
        if self.config.get("web_auto_start", False):
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
            self.config = APP_CONFIG
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
        for code, data in TRANSLATIONS.items():
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
            APP_CONFIG.update(self.config)
        except Exception:
            pass

    def auto_connect_device(self):
        """Uygulama açılınca NexDeck portu bulunursa otomatik bağlanır."""
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

    def try_reconnect(self):
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
        if resolved_data != data and MAIN_WINDOW:
            ui_log(f"{tr('log_signal')} {data} → {resolved_data}")

        cfg = buttons_cfg.get(resolved_data)
        if cfg and cfg.get("action"):
            if MAIN_WINDOW: ui_log(tr("found_task").format(cfg.get("name")))
            execute_macro(cfg["action"])
        else:
            if MAIN_WINDOW: ui_log(tr("no_assigned_task"))

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
        if MAIN_WINDOW and hasattr(MAIN_WINDOW, "log_area"):
            ui_log(tr("audio_apps_refresh_log"))

    def save_encoder_value(self, value, text=""):
        if value in ["__disabled_header__", "__no_audio_apps__", None]:
            return False
        if "encoder" not in self.config:
            self.config["encoder"] = {}
        self.config["encoder"]["turn"] = value
        save_config(self.config)
        if text and MAIN_WINDOW:
            ui_log(tr("encoder_changed_log").format(text))
        return True

    def process_encoder_pending_steps(self):
        steps = self.encoder_pending_steps
        self.encoder_pending_steps = 0
        if steps == 0:
            return

        enc_cfg = self.config.get("encoder", {})
        turn_action = enc_cfg.get("turn", "general_volume")
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
                if MAIN_WINDOW:
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

            if not changed and MAIN_WINDOW:
                ui_log(tr("audio_session_not_found"))

        except Exception as e:
            if MAIN_WINDOW:
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
    if UI_BRIDGE is None or _is_gui_thread():
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


class AppApi:
    """Yeni arayüzün kullandığı JSON API. remote=True: telefondan (LAN) gelen istek, kısıtlı yetki."""

    LOCAL_ONLY = {"device", "web", "known_device", "ui", "settings", "bg_image", "theme"}

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
        cfg = APP_CONFIG
        win = MAIN_WINDOW
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
        state = {
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
            "changelog": NEXSTUDIO_CHANGELOG.get(lang, NEXSTUDIO_CHANGELOG["tr"]),
            "device": {
                "connected": bool(win and win.is_device_connected()),
                "port": getattr(getattr(win, "serial_thread", None), "port", "") if win else "",
                "fw": getattr(win, "device_fw", "") if win else "",
                "hid": bool(getattr(win, "device_supports_hid", False)) if win else False,
            },
        }
        if not remote:
            state["settings"] = {
                "start_with_win": bool(cfg.get("start_with_win")),
                "run_in_bg": bool(cfg.get("run_in_bg")),
                "auto_connect": bool(cfg.get("auto_connect", True)),
                "key_send_mode": cfg.get("key_send_mode", "auto"),
                "elevated": is_process_elevated(),
            }
            state["device"]["ports"] = [{"label": label, "port": port} for label, port, _ in (win.scan_device_ports() if win else [])]
        return state

    @classmethod
    def get_live(cls, body, remote):
        """Arayüzün sık sorduğu hafif uç: son sinyaller (tuş/tekerlek) ve bağlantı durumu."""
        win = MAIN_WINDOW
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
    def get_audio_apps(cls, body, remote):
        win = MAIN_WINDOW
        apps = call_on_worker_sync(lambda: win.get_audio_mixer_apps()) if win else []
        options = [{"value": "general_volume", "label": "Genel ses"},
                   {"value": "active_window", "label": "Aktif pencerenin sesi"},
                   {"value": "brightness", "label": "Ekran parlaklığı"}]
        options += [{"value": value, "label": label} for label, value in (apps or [])]
        return {"ok": True, "options": options}

    @classmethod
    def get_web(cls, body, remote):
        win = MAIN_WINDOW
        running = bool(win and win.mobile_thread and win.mobile_thread.is_running)
        url = getattr(win, "current_web_url", "") if running else ""
        pin = APP_CONFIG.get("mobile_pin", "") if running else ""
        devices = []
        for dev_id, d in (APP_CONFIG.get("known_web_devices") or {}).items():
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
            old = (APP_CONFIG.get("buttons") or {}).get(sig) or {}
            entry = {"name": act, "category": cat, "action": action, "details": format_action_details(action),
                     "emoji": action_emoji(cat, act, action)}
            # Aynı göreve ayar değiştirilirken seçilmiş resim korunur
            if old.get("icon") and old.get("name") == act:
                entry["icon"] = old["icon"]
            if sig.startswith("NEX:P3_") or sig.startswith("NEX:P4_"):
                entry["btn_text"] = str(body.get("btn_text", old.get("btn_text", "")))[:20]
            APP_CONFIG.setdefault("buttons", {})[sig] = entry
            save_config(APP_CONFIG)
        cls._refresh_classic(sync_screen=sig.startswith("NEX:P3_") or sig.startswith("NEX:P4_"))
        return {"ok": True}

    @classmethod
    def post_clear(cls, body, remote):
        sig = str(body.get("sig", ""))
        with CONFIG_LOCK:
            (APP_CONFIG.get("buttons") or {}).pop(sig, None)
            save_config(APP_CONFIG)
        cls._refresh_classic(sync_screen=sig.startswith("NEX:P3_") or sig.startswith("NEX:P4_"))
        return {"ok": True}

    @classmethod
    def post_test(cls, body, remote):
        cfg = (APP_CONFIG.get("buttons") or {}).get(str(body.get("sig", "")))
        if not is_valid_user_task(cfg):
            raise ValueError("Bu tuşa görev atanmamış")
        ui_log(f"▶ {'Telefondan' if remote else 'Arayüzden'} çalıştırıldı: {cfg.get('name')}")
        execute_macro(cfg["action"])
        return {"ok": True}

    @classmethod
    def post_icon(cls, body, remote):
        sig = str(body.get("sig", ""))
        with CONFIG_LOCK:
            cfg = (APP_CONFIG.get("buttons") or {}).get(sig)
            if not is_valid_user_task(cfg):
                raise ValueError("Önce bu tuşa bir görev ata")
            if body.get("data"):
                cfg["icon"] = _save_data_url_image(body["data"], 160, "icon")
            elif body.get("emoji"):
                cfg["emoji"] = str(body["emoji"])[:8]
                cfg.pop("icon", None)
            else:
                cfg.pop("icon", None)
            save_config(APP_CONFIG)
        return {"ok": True, "icon": cfg.get("icon", "")}

    @classmethod
    def post_page_name(cls, body, remote):
        page = str(body.get("page", ""))
        if page not in ("1", "2", "3", "4"):
            raise ValueError("Geçersiz sayfa")
        with CONFIG_LOCK:
            APP_CONFIG.setdefault("page_names", {})[page] = str(body.get("name", "")).strip()[:20]
            save_config(APP_CONFIG)
        cls._refresh_classic()
        return {"ok": True}

    @classmethod
    def post_encoder(cls, body, remote):
        turn = str(body.get("turn", ""))
        if not turn:
            raise ValueError("Tekerlek ayarı boş")
        with CONFIG_LOCK:
            APP_CONFIG.setdefault("encoder", {})["turn"] = turn
            save_config(APP_CONFIG)
        cls._refresh_classic()
        return {"ok": True}

    @classmethod
    def post_volume(cls, body, remote):
        steps = max(-20, min(20, int(body.get("steps", 0))))
        win = MAIN_WINDOW
        if win and steps:
            run_on_ui(lambda: (setattr(win, "encoder_pending_steps", win.encoder_pending_steps + steps),
                               win.process_encoder_pending_steps()))
        return {"ok": True}

    # ----- profiller -----
    @classmethod
    def post_profile(cls, body, remote):
        op = body.get("op")
        name = str(body.get("name", "")).strip()[:40]
        win = MAIN_WINDOW
        if op == "switch":
            if name not in (APP_CONFIG.get("profiles") or {}):
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
        win = MAIN_WINDOW
        if key not in ("start_with_win", "run_in_bg", "auto_connect", "key_send_mode", "language"):
            raise ValueError("Bilinmeyen ayar")

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
            theme = {**DEFAULT_UI_THEME, **(APP_CONFIG.get("ui_theme") or {})}
            if body.get("mode") in ("dark", "light"):
                theme["mode"] = body["mode"]
            if re.match(r"^#[0-9A-Fa-f]{6}$", str(body.get("accent", ""))):
                theme["accent"] = body["accent"]
            if "bg_color" in body and (body["bg_color"] == "" or re.match(r"^#[0-9A-Fa-f]{6}$", str(body["bg_color"]))):
                theme["bg_color"] = body["bg_color"]
            if "glass" in body:
                theme["glass"] = max(0.3, min(1.0, float(body["glass"])))
            APP_CONFIG["ui_theme"] = theme
            save_config(APP_CONFIG)
        return {"ok": True, "theme": theme}

    @classmethod
    def post_bg_image(cls, body, remote):
        with CONFIG_LOCK:
            theme = {**DEFAULT_UI_THEME, **(APP_CONFIG.get("ui_theme") or {})}
            theme["bg_image"] = _save_data_url_image(body["data"], 2560, "bg", fmt="JPEG") if body.get("data") else ""
            APP_CONFIG["ui_theme"] = theme
            save_config(APP_CONFIG)
        return {"ok": True, "theme": theme}

    @classmethod
    def post_device(cls, body, remote):
        win = MAIN_WINDOW
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
        win = MAIN_WINDOW
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
            devices = APP_CONFIG.get("known_web_devices") or {}
            if dev_id not in devices:
                raise ValueError("Cihaz bulunamadı")
            if body.get("op") == "forget":
                devices.pop(dev_id, None)
            elif body.get("op") == "rename":
                devices[dev_id]["name"] = str(body.get("name", "")).strip()[:40]
            save_config(APP_CONFIG)
        run_on_ui(lambda: MAIN_WINDOW.refresh_web_security_panel())
        return {"ok": True}

    @classmethod
    def post_ui(cls, body, remote):
        op = body.get("op")
        win = MAIN_WINDOW
        if op == "classic":
            call_on_ui_sync(lambda: win.switch_ui_mode("classic"))
        elif op == "show":
            run_on_ui(win.open_preferred_ui)
        elif op == "open_plugins":
            os.startfile(PLUGINS_DIR)
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
        win = MAIN_WINDOW
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
    boot = json.dumps({"apiBase": api_base, "remote": remote, "auth": auth_query})
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


if __name__ == "__main__":
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
    MAIN_WINDOW = NexHubApp()
    MAIN_WINDOW.open_preferred_ui()
    
    sys.exit(app.exec_())

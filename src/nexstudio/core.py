# NexStudio — NEXSTUDIO ÖZGÜR YAZILIM LİSANSI (NPL-v2), Telif Hakkı (c) 2026 Ali Mert Taşcı / NexHub. Ayrıntılar: LICENSE.txt

"""Temel altyapı: kütüphaneler, dosya yolları, log, görev kuyruğu, SendInput tuş gönderimi, tek kopya."""
# flake8: noqa
from . import state

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
state.MAIN_WINDOW = None

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
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), relative_path)

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

_SMALL_LOGO_CACHE = []


def get_small_logo_data_uri(size=96):
    """Yeni arayüzün sol üstündeki logo: küçültülmüş PNG (sayfaya gömülür, ~10 KB)."""
    if _SMALL_LOGO_CACHE:
        return _SMALL_LOGO_CACHE[0]
    uri = ""
    try:
        from PIL import Image
        import io
        path = find_nexstudio_logo_path()
        if path:
            img = Image.open(path).convert("RGBA")
            img.thumbnail((size, size))
            buf = io.BytesIO()
            img.save(buf, "PNG", optimize=True)
            uri = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        uri = ""
    _SMALL_LOGO_CACHE.append(uri)
    return uri


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
NEXSTUDIO_BUILD_CHANNEL = "Public 2.7"
NEXSTUDIO_BUILD_ID = "NEX-270-AMT"
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
        ("2.8.0", "27.11.2026", [
            "Ebeveyn kontrolü: Ayarlar > Genel'den açılan 'Ebeveyn' bölümü; kişisel şifre ve kurtarma kodu, günlük süre ve kullanım saatleri, 7 günlük kullanım grafiği.",
            "Süre bitince tam ekran kilit: açık programlar kapanır, kilit boyunca hiçbir şey açılamaz; Win, Alt+Tab ve Görev Yöneticisi kısayolu çalışmaz. 5 dakika kala uyarı gelir.",
            "Ebeveyn kilit ekranından şifreyle ek süre verir ya da 30 dakikalık yönetici oturumu açar; Windows kilitlenince oturum kapanır. Saat değiştirilirse bilgisayar kilitlenir.",
            "Ebeveyn kontrolü açıkken NexStudio şifresiz kapatılamaz; kilitliyken NexDeck tuşları ve telefon görevleri çalışmaz.",
        ]),
        ("2.7.3", "27.11.2026", [
            "Telefonda 'Düzenle' modunda ekstra tekerlek eklenip değiştirilebilir; telefonun Ayarlar'ında web modu tuş düzeni (serbest ızgara) seçilebilir.",
            "Güvenlik: telefondan atanan web adresleri sıkı denetlenir ve tarayıcı komut satırı olmadan açılır; telefon kendini 'hatırlanan cihaz' yapamaz; masaüstü arayüzü başka sitelerden gelen isteklere kapalı.",
            "Çeviriler: kütüphane araması İngilizce/Almanca adlarla da çalışır, tekerlek hedefleri ve 56 eksik metin çevrildi.",
            "'Otomatik bağlan' kapalıyken cihazlı moda geçince cihaz aranmaz; ızgara boyutu seçimleri 'Sütun: 4' biçiminde.",
        ]),
        ("2.7.2", "27.11.2026", [
            "Güvenlik: telefondan 'Özel kısayol' ve 'Metin yazdırma' görevleri de atanamaz (yalnızca bilgisayardan); atanmış tuşa telefondan basmak çalışır.",
            "Telefondaki giriş, onay bekleniyor, engellendi ve 'kod değişti' sayfaları artık seçili dilde.",
            "Eklenti görevleri (Discord, Spotify, OBS, Zoom…) ve profil görevleri İngilizce/Almanca çevrildi.",
        ]),
        ("2.7.1", "27.11.2026", [
            "Düzen menüsü artık panellerin arkasında açılmıyor; üst çubuk gizliyken sağ alttaki 'Düzen' düğmesinden de açılır, 'Tümünü göster' eklendi.",
            "Ekstra tekerlek ekleme/düzenleme penceresi açılmıyordu; düzeltildi.",
            "Yenilikler paneli, gizli sol menü ve açılır pencereler: üst üste binme, dar ekranda taşma ve şeffaflıkta okunmama sorunları giderildi.",
            "Web: 'hatırlanan' bir cihaz artık atılabiliyor/unutulabiliyor; kod yenilenince telefon kilitlenmek yerine yeniden giriş ister; 'sadece izin verdiğim cihazlar' açıkken onay çalışır; cihazlar model adıyla görünür.",
            "Güvenlik: telefondan 'Özel Uygulama' görevi atanamaz (yalnızca bilgisayardan), web adresleri denetlenir.",
            "Serbest ızgara telefonda taşmıyor; cihaz listesi QR'a tıklayınca donmuyor.",
            "İngilizce/Almanca çeviriler tamamlandı; dil değişince eski dil ekranda kalmıyor.",
            "Hatalı isteklere sunucu hatası yerine açıklayıcı mesaj; seçilen emoji görev ayarı değişince korunuyor; 1. sayfadaki buton numaraları düzeltildi.",
        ]),
        ("2.7.0", "27.11.2026", [
            "Ekstra ses tekerlekleri: cihazın altına 6 taneye kadar sanal tekerlek ekle; her biri ayrı bir uygulamanın (ör. Discord, Spotify) sesini kontrol eder. Telefonda da çevrilebilir.",
            "Web modunda tuş düzeni seçimi: 'Cihazla aynı' (4 sayfa, ileride cihaza birebir geçer) ya da 'Serbest ızgara' (2–6 sütun, 1–4 satır, 8 sayfaya kadar).",
            "Web modunda alttaki fiziksel tuşlar gizlenir; sadece ekran ızgarası görünür.",
        ]),
        ("2.6.4", "27.11.2026", [
            "Otomatik güncelleme: NexStudio günde bir kez yeni sürüme bakar, haber verir; tek tıkla indirir, SHA-256 ile doğrular, kurar ve yeniden açılır.",
            "Kurulum artık kullanıcı klasörüne yapılıyor: kurulum ve güncellemeler yönetici izni (UAC) istemiyor.",
            "Program Files'ta kalan eski kopya için Ayarlar'da tek tıkla kaldırma önerisi.",
        ]),
        ("2.6.3", "27.11.2026", [
            "Web sayfasında bağlanan tüm cihazlar: şu an bağlı olanlar, son görülme, hatırlananlar.",
            "Her cihaz için Bağlantıyı kes, Engelle / Engeli kaldır, İzin ver, Adlandır, Unut.",
            "Erişim modu senin seçimin: sadece PIN, sadece bilgisayardan onay ya da PIN + onay. Onay penceresinde 'Bu cihazı hatırla' seçilebilir; 60 sn içinde cevap gelmezse bağlantı reddedilir.",
            "'Sadece izin verdiğim cihazlar' açıkken izinsiz cihazlar PIN'i bilse de bağlanamaz; denemeleri listede görünür, tek tıkla izin verilir.",
            "Telefonda PIN artık adres çubuğunda kalmıyor; giriş güvenli bir oturum çereziyle sürüyor.",
        ]),
        ("2.6.2", "27.11.2026", [
            "Odak modu (F11): menüler gizlenir, ekranda sadece cihaz kalır; köşedeki butonla ya da F11 ile geri açılır.",
            "Üst çubuktaki Düzen menüsünden sol menü, üst çubuk, görev listesi ve tuş ayarları ayrı ayrı gizlenebilir. Gizli sol menü fare sol kenara gelince açılır.",
            "Pencerenin başlık çubuğu uygulamanın arka plan rengini alır (Windows 11); üst çubuk daha saydam.",
        ]),
        ("2.6.1", "27.11.2026", [
            "Sol üstte NexStudio logosu.",
            "\"Telefon\" sekmesi artık \"Web\": telefon, tablet ya da başka bir bilgisayardan kontrol.",
            "Profil oluşturma, silme ve adlandırma artık uygulamanın kendi pencerelerinde (tarayıcının \"127.0.0.1 diyor ki\" kutusu yok).",
            "Ekran önizlemesinde ◀ ▶ butonları gerçek cihazdaki gibi sayfa değiştirir.",
            "Yenilikler paneli butona tekrar basınca ya da dışarı tıklayınca kapanır.",
            "Geliştirici modu (Ayarlar > Gelişmiş): COM portu, firmware bilgisi ve canlı Günlük sekmesi sadece açıkken görünür.",
        ]),
        ("2.6", "27.11.2026", [
            "Web modu: NexDeck'in yoksa telefonun sanal NexDeck olur. Ayarlar'dan tek tıkla cihazlı sürüme geçebilirsin; tuş atamaların aynen kalır.",
            "İlk açılışta karşılama ekranı: cihazın var mı, yok mu seç; dili seç.",
            "Dil paketleri: arayüz İngilizce ve Almanca da kullanılabilir. Yeni dil eklemek için tek bir dil dosyası ya da dil eklentisi yeterli.",
            "NexDeck'i kendin yap rehberi: parça listesi, bağlantılar ve yükleme adımları (docs/DONANIM.md).",
        ]),
        ("2.5.1", "27.11.2026", [
            "Telefondan kontrol bazen 'Yetkisiz' hatası veriyordu: iki program aynı web portunu paylaşabiliyordu. Port artık özel kullanımda.",
            "Kod tek dosyadan modüllere bölündü (geliştirme altyapısı; görünüşte değişiklik yok).",
        ]),
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
        ("2.8.0", "2026-11-27", [
            "Parental control: a 'Parental' section enabled in Settings > General; personal password and recovery code, daily time and allowed hours, 7-day usage chart.",
            "When time is up a full-screen lock appears: open programs are closed and nothing can be opened while locked; Win, Alt+Tab and the Task Manager shortcut are blocked. Warning 5 minutes before.",
            "On the lock screen the parent can grant extra time with the password or open a 30-minute parent session, which ends when Windows is locked. Changing the clock locks the computer.",
            "While parental control is on, NexStudio can't be closed without the password; NexDeck keys and phone tasks don't run while locked.",
        ]),
        ("2.7.3", "2026-11-27", [
            "In 'Edit' mode the phone can add and change extra wheels; the phone's Settings can switch the web-mode key layout (free grid).",
            "Security: web addresses assigned from the phone are strictly validated and the browser opens without a command shell; a phone can't make itself a 'remembered device'; the desktop UI rejects requests from other sites.",
            "Translations: library search works with English/German names; wheel targets and 56 missing texts translated.",
            "With 'Auto connect' off, switching to device mode no longer searches for the device; grid size options read 'Columns: 4'.",
        ]),
        ("2.7.2", "2026-11-27", [
            "Security: 'Custom shortcut' and 'Type text' tasks can no longer be assigned from the phone either (computer only); pressing an assigned key from the phone still works.",
            "The phone's sign-in, waiting-for-approval, blocked and 'code changed' pages now use the selected language.",
            "Plugin tasks (Discord, Spotify, OBS, Zoom…) and profile tasks translated to English/German.",
        ]),
        ("2.7.1", "2026-11-27", [
            "The Layout menu no longer opens behind the panels; with the top bar hidden it opens from the 'Layout' button at the bottom right, and 'Show all' was added.",
            "The add/edit extra wheel dialog did not open; fixed.",
            "What's new panel, hidden side menu and dialogs: overlapping, overflow on narrow windows and unreadable transparency fixed.",
            "Web: a 'remembered' device can now be kicked/forgotten; after a new code the phone asks to sign in again instead of freezing; approval works with 'only devices I allow'; devices show their model name.",
            "Security: the 'Custom app' task cannot be assigned from the phone (computer only), web addresses are validated.",
            "Free grid fits on phones; the device list no longer freezes after clicking the QR code.",
            "English/German translations completed; switching language no longer leaves the old language on screen.",
            "Clear messages instead of server errors for bad requests; a chosen emoji is kept when task settings change; button numbers on page 1 fixed.",
        ]),
        ("2.7.0", "2026-11-27", [
            "Extra volume wheels: add up to 6 virtual wheels under the device; each controls its own app (e.g. Discord, Spotify). They turn on the phone too.",
            "Key layout choice in web mode: 'Same as device' (4 pages, carries over to a NexDeck later) or 'Free grid' (2–6 columns, 1–4 rows, up to 8 pages).",
            "In web mode the physical keys row is hidden; only the screen grid is shown.",
        ]),
        ("2.6.4", "2026-11-27", [
            "Automatic updates: NexStudio checks for a new version once a day, lets you know, then downloads, verifies (SHA-256), installs and restarts with one click.",
            "NexStudio now installs into your user folder: installing and updating no longer ask for administrator permission (UAC).",
            "Settings offer a one-click removal of an old copy left in Program Files.",
        ]),
        ("2.6.3", "2026-11-27", [
            "The Web page lists every device that connected: online now, last seen, remembered.",
            "Per device: Disconnect, Block / Unblock, Allow, Rename, Forget.",
            "You choose the access mode: PIN only, approval on this computer only, or PIN + approval. The approval dialog can remember the device; requests are denied after 60 seconds.",
            "With 'Only devices I allow', devices without permission can't connect even with the PIN; their attempts appear in the list and can be allowed with one click.",
            "The PIN no longer stays in the phone's address bar; the session continues with a secure cookie.",
        ]),
        ("2.6.2", "2026-11-27", [
            "Focus mode (F11): menus hide and only the device stays on screen; bring them back with the corner button or F11.",
            "The Layout menu in the top bar hides the side menu, top bar, action list and key settings separately. A hidden side menu opens when the mouse reaches the left edge.",
            "The window title bar takes the app's background color (Windows 11); the top bar is more transparent.",
        ]),
        ("2.6.1", "2026-11-27", [
            "NexStudio logo in the top-left corner.",
            "The \"Phone\" tab is now \"Web\": control from a phone, tablet or another computer.",
            "Creating, deleting and renaming profiles now uses the app's own dialogs.",
            "The ◀ ▶ buttons in the screen preview switch pages like on the real device.",
            "The What's new panel closes when you press its button again or click outside.",
            "Developer mode (Settings > Advanced): COM port, firmware details and a live Log tab only show when it is on.",
        ]),
        ("2.6", "2026-11-27", [
            "Web mode: without a NexDeck your phone becomes a virtual NexDeck. Switch to device mode from Settings at any time; your key assignments stay.",
            "Welcome screen on first launch: choose whether you have a NexDeck and pick a language.",
            "Language packs: the interface is available in English and German. Adding a language needs just one language file or a language plugin.",
            "Build-your-own NexDeck guide: parts list, wiring and upload steps (docs/DONANIM.md).",
        ]),
        ("2.5.1", "2026-11-27", [
            "Fixed occasional 'Unauthorized' errors on phone control: two apps could share the same web port.",
            "Code split into modules (no visible change).",
        ]),
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

APP_VERSION = "2.8.0"
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


state.UI_BRIDGE = None
_PENDING_UI_LOGS = []


def _is_gui_thread():
    return threading.current_thread() is threading.main_thread()


# 2.6.1: Yeni arayüzün geliştirici modundaki "Günlük" sayfası için son mesajlar (thread-güvenli deque)
import collections as _collections
LOG_BUFFER = _collections.deque(maxlen=600)
_LOG_SEQ = [0]
_LOG_LOCK = threading.Lock()


def ui_log(message):
    """Her thread'den güvenle çağrılabilir; mesaj GUI thread'inde log alanına eklenir."""
    text = str(message)
    with _LOG_LOCK:
        _LOG_SEQ[0] += 1
        LOG_BUFFER.append((_LOG_SEQ[0], datetime.now().strftime("%H:%M:%S"), text))
    if state.UI_BRIDGE is None:
        _PENDING_UI_LOGS.append(text)
        return
    if _is_gui_thread():
        _append_log_now(text)
    else:
        state.UI_BRIDGE.log_signal.emit(text)


def _append_log_now(text):
    if state.MAIN_WINDOW is not None and hasattr(state.MAIN_WINDOW, "log_area"):
        state.MAIN_WINDOW.log_area.append(f"[{datetime.now().strftime('%H:%M:%S')}] {text}")
    else:
        _PENDING_UI_LOGS.append(text)


def run_on_ui(fn):
    """Bir fonksiyonu GUI thread'inde çalıştırır (web/makro thread'lerinden arayüz güncellemek için)."""
    if state.UI_BRIDGE is None or _is_gui_thread():
        fn()
    else:
        state.UI_BRIDGE.call_signal.emit(fn)


def init_ui_bridge():
    if state.UI_BRIDGE is None:
        state.UI_BRIDGE = UiBridge()
        state.UI_BRIDGE.log_signal.connect(_append_log_now)


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


state._SINGLE_INSTANCE_HANDLE = None


def acquire_single_instance():
    """
    Aynı anda iki NexStudio açılırsa ikisi de aynı COM portunu kapmaya çalışır ve
    tuşlar 'bazen' çalışmaz. Windows named mutex ile tek kopya garantilenir.
    """
    try:
        name = "Local\\NexStudio_SingleInstance_" + hashlib.md5(APP_DIR.lower().encode("utf-8")).hexdigest()[:12]
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        state._SINGLE_INSTANCE_HANDLE = kernel32.CreateMutexW(None, False, name)
        return ctypes.get_last_error() != 183  # ERROR_ALREADY_EXISTS
    except Exception:
        return True


def release_single_instance():
    if state._SINGLE_INSTANCE_HANDLE:
        try:
            ctypes.windll.kernel32.CloseHandle(state._SINGLE_INSTANCE_HANDLE)
        except Exception:
            pass
        state._SINGLE_INSTANCE_HANDLE = None


def relaunch_as_admin():
    """Uygulamayı yönetici olarak yeniden başlatır (UAC onayı istenir)."""
    if getattr(sys, "frozen", False):
        exe, params = sys.executable, " ".join(f'"{a}"' for a in sys.argv[1:])
    else:
        exe, params = sys.executable, " ".join(f'"{a}"' for a in sys.argv)
    rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
    return rc > 32

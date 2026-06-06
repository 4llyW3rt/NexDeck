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
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QTabWidget, QMessageBox, QTextEdit, 
    QListWidget, QListWidgetItem, QGroupBox, QColorDialog, QLineEdit,
    QSystemTrayIcon, QMenu, QAction, QScrollArea, QFrame, QSizePolicy, QFileDialog, QInputDialog, QSplitter, QDialog, QStackedWidget, QGraphicsOpacityEffect
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty, QRect, QPoint
from PyQt5.QtGui import QFont, QCursor, QColor, QIcon, QPixmap, QImage, QPainter, QPen

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
    appdata = os.getenv('APPDATA')
    path = os.path.join(appdata, "NexStudio")
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

APP_DIR = get_appdata_path()
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
PLUGINS_DIR = os.path.join(APP_DIR, "plugins")
LOCALES_DIR = os.path.join(APP_DIR, "locales")
NIRCMD_PATH = get_resource_path("nircmd.exe")
APP_ICON_PATH = get_resource_path("app_icon.ico")
NEXHUB_YOUTUBE_CHANNEL = "https://www.youtube.com/@NexHubCo"

# Gizli sahiplik işaretleri / telif doğrulama notları
NEXSTUDIO_LICENSE_NAME = "NEXSTUDIO ÖZGÜR YAZILIM LİSANSI (NPL-v2)"
NEXSTUDIO_COPYRIGHT = "Telif Hakkı (c) 2026 - Ali Mert Taşcı / NexHub"
NEXSTUDIO_OWNER_SIGNATURE = "Ali Mert Taşcı|@tatarmantan|tatarmantan@gmail.com"
NEXSTUDIO_PROVENANCE_MARKERS = [
    "NPL-v2:AMT:CORE",
    "NEXSTUDIO:AUTHOR:ALI_MERT_TASCI",
    "NEXHUB:OWNER:ALI_MERT_TASCI",
    "NEXHUB:PROJECT_BRAND",
    "NEXSTUDIO:COMMUNITY_FREE_ONLY",
]

# =========================================================
# GÜNCELLEME REHBERİ / CHANGELOG
# Burayı düzenleyerek başlangıç ekranındaki "Güncelleme Rehberi" kartını
# kolayca değiştirebilirsin. Dil aktif dile göre otomatik seçilir.
# Format:
#   ("Tarih", "Son kullanıcının anlayacağı kısa açıklama")
# =========================================================
NEXSTUDIO_CHANGELOG = {
    "tr": [
        ("06.06.2026", "Arayüz düzeni sadeleştirildi; ikonlar, başlıklar ve gezinme yapısı daha okunaklı hale getirildi."),
        ("06.06.2026", "Tekerlek ayarı yalnızca Tekerlek Butonu panelinden yönetilecek şekilde düzenlendi."),
        ("06.06.2026", "Ses kontrolü %1 adımlı hale getirildi ve Windows ses karıştırıcısı ile daha uyumlu çalışacak şekilde yenilendi."),
        ("06.06.2026", "Web Kontrolü ve Hesap özellikleri ayrıştırıldı; geliştirme aşamasındaki bölümler kullanıcı için daha net gösterildi."),
    ],
    "en": [
        ("2026-06-06", "The interface layout was simplified; icons, headings, and navigation were made easier to read."),
        ("2026-06-06", "Wheel settings are now managed only from the Wheel Button panel."),
        ("2026-06-06", "Volume control now works in 1% steps and is better aligned with the Windows volume mixer."),
        ("2026-06-06", "Web Control and Account features were separated and marked clearly as in-development areas."),
    ],
}

if not os.path.exists(PLUGINS_DIR): os.makedirs(PLUGINS_DIR)
if not os.path.exists(LOCALES_DIR): os.makedirs(LOCALES_DIR)

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
        "mobile_server": "📱 Mobil Sunucuyu Başlat", "mobile_stop": "📱 Mobil Sunucuyu Durdur", "copy_web_url": "🔗 Web bağlantısını kopyala", "web_url_copied": "Web bağlantısı kopyalandı",
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
        "mobile_server": "📱 Start Mobile Server", "mobile_stop": "📱 Stop Mobile Server", "copy_web_url": "🔗 Copy web link", "web_url_copied": "Web link copied",
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
                    TRANSLATIONS[lang_code].update(file_data)
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
    'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73, 'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77, 'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B
}

def press_key(vk_code):
    ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
    ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)

def get_physical_buttons():
    return {
        "BTN:1": tr("btn_1"), "BTN:2": tr("btn_2"), "BTN:3": tr("btn_3"), "BTN:4": tr("btn_4"), "BTN:5": tr("btn_5"), 
        "BTN:1:LONG": tr("btn_1_l"), "BTN:2:LONG": tr("btn_2_l"), "BTN:3:LONG": tr("btn_3_l"), "BTN:4:LONG": tr("btn_4_l"), "BTN:5:LONG": tr("btn_5_l"), 
        "ENC:BTN": tr("enc_btn")
    }

NEXTION_OBJ_MAP = {
    3:["b0", "b1", "b2", "b3", "b7", "b4", "b5", "b6"],
    4:["b1", "b2", "b3", "b4", "b0", "b5", "b7", "b6"]
}

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
        tr("cat_tools"): {
            tr("act_tool_exp"): {"type": "cmd", "cmd": "explorer.exe"},
            tr("act_tool_calc"): {"type": "cmd", "cmd": "calc.exe"},
            tr("act_tool_task"): {"type": "cmd", "cmd": "taskmgr.exe"}
        }
    }

FACTORY_DEFAULT_BUTTONS = {
    "NEX:P1_B1": {"name": "F13", "action": {"type": "native", "vk": VK_F13}},
    "NEX:P1_B2": {"name": "F14", "action": {"type": "native", "vk": VK_F14}},
    "NEX:P1_B3": {"name": "F15", "action": {"type": "native", "vk": VK_F15}},
    "NEX:P1_B4": {"name": "F16", "action": {"type": "native", "vk": VK_F16}},
    "NEX:P1_B5": {"name": "F17", "action": {"type": "native", "vk": VK_F17}},
    "NEX:P1_B6": {"name": "F18", "action": {"type": "native", "vk": VK_F18}},
    "NEX:P1_B7": {"name": "F19", "action": {"type": "native", "vk": VK_F19}},
    "NEX:P2_B1": {"name": "Önceki Şarkı", "action": {"type": "native", "vk": VK_MEDIA_PREV_TRACK}},
    "NEX:P2_B2": {"name": "Oynat/Duraklat", "action": {"type": "native", "vk": VK_MEDIA_PLAY_PAUSE}},
    "NEX:P2_B3": {"name": "Sonraki Şarkı", "action": {"type": "native", "vk": VK_MEDIA_NEXT_TRACK}},
    "NEX:P2_B4": {"name": "F20", "action": {"type": "native", "vk": VK_F20}},
    "NEX:P2_B6": {"name": "YouTube", "action": {"type": "web", "cmd": "https://www.youtube.com/@NexHubCo/@NexHubCo"}},
    "NEX:P2_B7": {"name": "Kick", "action": {"type": "web", "cmd": "https://kick.com"}}
}

LOADED_PLUGINS = {}
def load_plugins():
    global LOADED_PLUGINS
    LOADED_PLUGINS = {}
    for file_path in glob.glob(os.path.join(PLUGINS_DIR, "*.py")):
        module_name = os.path.basename(file_path)[:-3]
        try:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "PLUGIN_NAME") and hasattr(module, "ACTIONS"):
                LOADED_PLUGINS[module.PLUGIN_NAME] = {"actions": module.ACTIONS, "module": module}
        except:
            pass

def get_all_macros():
    all_macros = get_builtin_macros()
    for plugin_name, plugin_data in LOADED_PLUGINS.items():
        all_macros[f"🧩 {plugin_name}"] = plugin_data["actions"]
    return all_macros

def load_config():
    global APP_CONFIG
    default_cfg = {
        "language": "tr", "last_port": "", "accent_color": "#3B82F6", 
        "run_in_bg": False, "start_with_win": False, "screen_bg": "", 
        "mobile_pin": "", "web_token": "", "logged_in_email": "",
        "encoder": {"turn": "general_volume"},
        "page_names": {},
        "buttons": FACTORY_DEFAULT_BUTTONS.copy()
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f: 
                data = json.load(f)
                for k, v in data.items():
                    if isinstance(v, dict) and k in default_cfg:
                        default_cfg[k].update(v)
                    else:
                        default_cfg[k] = v
        except:
            pass
    
    if not default_cfg.get("web_token"):
        default_cfg["web_token"] = secrets.token_urlsafe(8)
    
    # Eski sürümlerde kayıtlı varsayılan sayfa adlarını dile göre yeniden çevrilebilir bırak.
    if "page_names" in default_cfg:
        for _n in ["1", "2", "3", "4"]:
            if default_cfg["page_names"].get(_n) in [f"Sayfa {_n}", f"Page {_n}"]:
                default_cfg["page_names"].pop(_n, None)

    APP_CONFIG = default_cfg
    return default_cfg

def save_config(config_data):
    global APP_CONFIG
    APP_CONFIG = config_data
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4)

def execute_macro(action):
    try:
        if action["type"] == "native":
            press_key(action["vk"])
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
            for vk in vk_list: ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
            for vk in reversed(vk_list): ctypes.windll.user32.keybd_event(vk, 0, 2, 0)
        elif action["type"] == "plugin":
            if action["plugin_name"] in LOADED_PLUGINS:
                module = LOADED_PLUGINS[action["plugin_name"]]["module"]
                if hasattr(module, "execute"):
                    module.execute(action["function"])
    except Exception as e:
        if MAIN_WINDOW: MAIN_WINDOW.log_area.append(f"⚠️ Makro Hatası: {str(e)}")

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

class MobileHandler(BaseHTTPRequestHandler):
    server_version = "NexDeckWeb"
    sys_version = ""
    def log_message(self, format, *args):
        # PyInstaller windowed modda konsol olmayacağı için sessiz çalışsın.
        return

    def send_html(self, html, code=200):
        # Bu handler'da header satırları bazı ortamlarda HTML gövdesine karışabildiği için
        # web panelinde yalnızca HTML gövdesini yazıyoruz.
        # Tarayıcı HTML'i yine doğru şekilde render eder; üstte HTTP/1.1 yazısı görünmez.
        data = html.encode("utf-8", errors="replace")
        try:
            self.wfile.write(data)
            self.wfile.flush()
        except Exception:
            pass
        self.close_connection = True

    def do_GET(self):
        token = APP_CONFIG.get("web_token", "")
        if self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        if not self.path.startswith(f"/{token}"):
            self.send_html("<h2>Yetkisiz erişim</h2><p>Lütfen NexDeck QR kodunu tekrar okutun.</p>", 403)
            return

        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        pin = params.get('pin', [''])[0]
        correct_pin = APP_CONFIG.get("mobile_pin", "")

        if pin != correct_pin:
            login_html = f"""
            <html><head><meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
            :root {{
                --accent: {APP_CONFIG.get('accent_color', '#3B82F6')};
                --bg: #070B14;
                --card: rgba(15, 23, 42, .78);
                --border: rgba(148, 163, 184, .18);
                --text: #F8FAFC;
                --muted: #94A3B8;
            }}
            * {{ box-sizing: border-box; }}
            body {{
                min-height: 100vh; margin: 0; color: var(--text);
                font-family: Inter, 'Segoe UI', Roboto, Arial, sans-serif;
                background:
                    radial-gradient(circle at 20% 10%, rgba(59,130,246,.24), transparent 34%),
                    radial-gradient(circle at 80% 0%, rgba(139, 92, 246, .22), transparent 32%),
                    linear-gradient(145deg, #050814 0%, #0B1220 50%, #111827 100%);
                display: grid; place-items: center; padding: 22px;
            }}
            .login-card {{
                width: min(420px, 100%);
                background: var(--card);
                border: 1px solid var(--border);
                border-radius: 28px;
                padding: 28px;
                box-shadow: 0 26px 90px rgba(0,0,0,.42);
                backdrop-filter: blur(22px);
            }}
            .brand {{ display:flex; align-items:center; gap:14px; margin-bottom: 22px; }}
            .logo {{
                width: 48px; height: 48px; border-radius: 16px;
                display:grid; place-items:center; font-weight: 900; font-size: 22px;
                background: var(--accent); color: white;
                box-shadow: 0 12px 38px rgba(59,130,246,.32);
            }}
            h2 {{ margin:0; font-size:26px; letter-spacing:-.02em; }}
            p {{ color: var(--muted); margin: 8px 0 24px; line-height:1.55; }}
            input {{
                width:100%; padding: 18px 16px; border-radius: 18px;
                background: rgba(2, 6, 23, .58); color: white;
                border: 1px solid var(--border); outline: none;
                text-align:center; font-size:22px; letter-spacing: 8px; font-weight: 900;
                text-transform: uppercase; margin-bottom: 14px;
            }}
            input:focus {{ border-color: var(--accent); box-shadow: 0 0 0 4px rgba(59,130,246,.18); }}
            button {{
                width:100%; border:0; border-radius:18px; padding: 17px 18px;
                background: var(--accent); color:#fff; font-size:16px; font-weight:900;
                cursor:pointer; box-shadow: 0 16px 44px rgba(59,130,246,.30);
                transition: transform .18s ease, filter .18s ease;
            }}
            button:active {{ transform: scale(.98); }}
            .hint {{ font-size: 13px; margin-top: 14px; text-align:center; color: var(--muted); }}
            </style></head><body>
            <main class="login-card">
                <div class="brand">
                    <div class="logo">N</div>
                    <div>
                        <h2>NexStudio</h2>
                        <p style="margin:3px 0 0;">Web Kontrolü</p>
                    </div>
                </div>
                <p>Lütfen bilgisayar ekranındaki 6 haneli PIN kodunu girin.</p>
                <form action="/{token}" method="GET">
                    <input type="text" name="pin" placeholder="PIN" maxlength="6" required autocomplete="off"><br>
                    <button type="submit">Giriş Yap</button>
                </form>
                <div class="hint">Güvenli bağlantı için QR kodu tekrar okutabilirsin.</div>
            </main>
            </body></html>
            """
            self.send_html(login_html)
            return

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

        if self.path.startswith(f'/{token}/api/save'):
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
                        MAIN_WINDOW.change_master_volume(delta)
                    elif mode in ["brightness", "Ekran Parlaklığı", "Screen Brightness"]:
                        brightness_delta = max(-20, min(20, steps if direction == "up" else -steps))
                        execute_macro({"type": "nircmd", "cmd": f"changebrightness {brightness_delta}"})
                    else:
                        MAIN_WINDOW.change_app_volume(mode, delta)
            except Exception as e:
                if MAIN_WINDOW and hasattr(MAIN_WINDOW, "log_area"):
                    MAIN_WINDOW.log_area.append(f"Web volume error: {e}")
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


        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        
        macros_json = json.dumps(get_all_macros(), ensure_ascii=False)
        buttons_json = json.dumps(get_physical_buttons(), ensure_ascii=False)
        translations_json = json.dumps(TRANSLATIONS, ensure_ascii=False)
        page_names_json = json.dumps(APP_CONFIG.get("page_names", {}), ensure_ascii=False)
        encoder_json = json.dumps(APP_CONFIG.get("encoder", {}), ensure_ascii=False)
        
        try:
            audio_apps_json = json.dumps(MAIN_WINDOW.get_audio_mixer_apps() if MAIN_WINDOW else [], ensure_ascii=False)
        except Exception:
            audio_apps_json = json.dumps([], ensure_ascii=False)
        
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
                    display:grid; place-items:center; background: var(--accent); color:white;
                    font-weight: 950; font-size: 22px;
                    box-shadow: 0 16px 44px rgba(59,130,246,.28);
                }}
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
        
        <div class="header">
            <h1>NexStudio</h1>
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
            const macros = {macros_json};
            const physBtns = {buttons_json};
            const i18n = {translations_json};
            let pageNames = {page_names_json};
            let encoderConfig = {encoder_json};
            let audioApps = {audio_apps_json};
            let currentConfig = {json.dumps(APP_CONFIG.get("buttons", {}), ensure_ascii=False)};
            let currentLang = localStorage.getItem('nex_lang') || '{APP_CONFIG.get("language", "tr")}';
            
            function t(key) {{
                if (i18n[currentLang] && i18n[currentLang][key]) return i18n[currentLang][key];
                return i18n['tr'][key] || key;
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
                    let name = currentConfig[sig] ? currentConfig[sig].name : t('empty');
                    htmlPhys += `<button class="btn-ctrl" onclick="fetch('/${{token}}/exec?sig=${{sig}}&pin=${{pin}}')"><b>${{physBtns[sig]}}</b><span>${{name}}</span></button>`;
                }}
                document.getElementById('ctrl-list-phys').innerHTML = htmlPhys;
                
                let page = document.getElementById('ctrl-page').value;
                let htmlScr = "";
                document.getElementById('touch-page-label').innerText = `${{t('page_' + page) || 'Page ' + page}}`;
                for (let i=1; i<=8; i++) {{
                    let hidden = (page == 1 && i == 8) || (page > 1 && (i == 5 || i == 8));
                    if (hidden) {{
                        htmlScr += `<button class="touch-btn hidden-slot" tabindex="-1"></button>`;
                        continue;
                    }}
                    let sig = `NEX:P${{page}}_B${{i}}`;
                    let cfg = currentConfig[sig] || {{}};
                    let name = cfg.name || t('empty');
                    let text = (page >= 3 && cfg.btn_text) ? cfg.btn_text : `Buton ${{i}}`;
                    let emptyClass = cfg.name ? '' : ' empty';
                    htmlScr += `<button class="touch-btn${{emptyClass}}" onclick="fetch('/${{token}}/exec?sig=${{sig}}&pin=${{pin}}')"><span class="top">${{text}}</span><span class="sub">${{name}}</span></button>`;
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
                    
                    for (let i=1; i<=8; i++) {{
                        if (page == 1 && i == 8) continue;
                        if (page > 1 && (i == 5 || i == 8)) continue;
                        let sig = `NEX:P${{page}}_B${{i}}`;
                        let name = currentConfig[sig] ? currentConfig[sig].name : t('empty');
                        btnSel.innerHTML += `<option value="${{sig}}">Buton ${{i}} (${{name}})</option>`;
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
                
                fetch(`/${{token}}/api/save?sig=${{sig}}&cat=${{cat}}&act=${{act}}&arg=${{arg}}&browser=${{browser}}&app_action=${{app_action}}&btn_text=${{btn_text}}&pin=${{pin}}`).then(() => {{
                    document.getElementById('save-msg').style.display = "block";
                    setTimeout(() => document.getElementById('save-msg').style.display = "none", 2000);
                    currentConfig[sig] = {{name: act, btn_text: btn_text}};
                    renderControlList();
                    updateAssignUI();
                    loadCurrentAssign();
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
            initWebWheel();
            setTimeout(refreshMixerApps, 500);
        </script>
        </body></html>
        """
        self.send_html(dashboard_html)

class MobileServerThread(QThread):
    def __init__(self):
        super().__init__()
        self.server = None
        self.is_running = False
    def run(self):
        try:
            self.server = HTTPServer(('0.0.0.0', 45729), MobileHandler)
            self.is_running = True
            self.server.serve_forever()
        except: pass
    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        self.is_running = False

# =========================================================
# 6. SERİ PORT HABERLEŞMESİ (ARDUINO)
# =========================================================
class SerialThread(QThread):
    data_received = pyqtSignal(str)
    connection_error = pyqtSignal(str)
    def __init__(self, port):
        super().__init__()
        self.port = port
        self.serial_conn = None
        self.is_running = True
    def run(self):
        try:
            self.serial_conn = serial.Serial(self.port, 9600, timeout=1)
            time.sleep(2)
            while self.is_running:
                if self.serial_conn.in_waiting > 0:
                    data = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if data: self.data_received.emit(data)
                time.sleep(0.01)
        except Exception as e: self.connection_error.emit(str(e))
    def send_data(self, data_str):
        if self.serial_conn and self.serial_conn.is_open:
            try: self.serial_conn.write(data_str.encode('iso-8859-9', errors='replace'))
            except:
                try: self.serial_conn.write(data_str.encode('utf-8', errors='ignore'))
                except: pass
    def stop(self):
        self.is_running = False
        if self.serial_conn and self.serial_conn.is_open: self.serial_conn.close()

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

    QWidget#AppRoot {{
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
        self.lbl_body.setStyleSheet("color: #E5ECF6; font-size: 13px; line-height: 1.5;")
        layout.addWidget(self.lbl_body)
        layout.addStretch()
        self.set_entries(entries)
        self.refresh_style()

    def set_entries(self, entries):
        self.entries = entries
        html_parts = []
        for date_text, desc in entries:
            html_parts.append(
                f'<div style="margin-top:8px; color:#A7B8D0; font-size:11px; font-weight:700;">{date_text}</div>'
                f'<div style="margin-top:4px; color:#F8FAFC; font-size:13px;">• {desc}</div>'
            )
        self.lbl_body.setText("".join(html_parts))

    def refresh_style(self):
        if self._hovered:
            self.setStyleSheet(
                "QFrame#ChangelogHoverCard { background-color: #101A2D; border: 1px solid {accent_color}; border-radius: 24px; }"
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
        load_locales()
        load_plugins()
        self.serial_thread = None
        self.mobile_thread = None
        self.current_signal = None
        self.setWindowTitle("NexStudio")
        self.setMinimumSize(1100, 750)
        self.apply_theme()
        self.init_ui()
        self.setup_tray()
        self.encoder_pending_steps = 0
        self.encoder_flush_timer = QTimer(self)
        self.encoder_flush_timer.setSingleShot(True)
        self.encoder_flush_timer.timeout.connect(self.process_encoder_pending_steps)
        self.apply_startup_setting()


    def resizeEvent(self, event):
        super().resizeEvent(event)


    def current_accent(self):
        return self.config.get("accent_color", "#3B82F6")

    def apply_theme(self):
        self.setStyleSheet(get_stylesheet(self.current_accent()))

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
            self.nav_buttons.append(btn)
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()
        self.quick_card = QWidget()
        self.quick_card.setObjectName("HeroCard")
        quick_l = QVBoxLayout(self.quick_card)
        quick_l.setContentsMargins(16, 16, 16, 16)
        quick_title = QLabel(tr("device_status"))
        quick_title.setObjectName("SectionTitle")
        self.lbl_sidebar_status = QLabel(tr("status_waiting"))
        self.lbl_sidebar_status.setObjectName("StatusPill")
        quick_l.addWidget(quick_title)
        quick_l.addWidget(self.lbl_sidebar_status)
        quick_hint = QLabel(tr("sidebar_status_hint"))
        quick_hint.setObjectName("Muted")
        quick_hint.setWordWrap(True)
        quick_l.addWidget(quick_hint)
        sidebar_layout.addWidget(self.quick_card)

        root_layout.addWidget(self.sidebar)

        content = QWidget()
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
        title_box.addWidget(self.lbl_page_title)
        title_box.addWidget(self.lbl_page_subtitle)
        topbar_layout.addLayout(title_box)
        topbar_layout.addStretch()

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
        content_layout.addWidget(self.stack)
        self.toast = ToastLabel(self.sidebar)

        self.setup_home_tab()
        self.setup_physical_tab()
        self.setup_screen_tab()
        self.setup_log_tab()
        self.setup_settings_tab()
        self.setup_web_tab()

        root_layout.addWidget(content)
        self.switch_main_page(0)

    def get_changelog_entries(self):
        lang = self.config.get("language", "tr")
        if lang in NEXSTUDIO_CHANGELOG:
            return NEXSTUDIO_CHANGELOG[lang]
        return NEXSTUDIO_CHANGELOG.get("tr", [])

    def get_changelog_hint(self):
        if self.config.get("language", "tr") == "en":
            return "Hover to expand and read the full changelog."
        return "Üzerine gelince kart genişler ve tüm değişiklikler okunur hale gelir."

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
        desc = QLabel(tr("home_desc"))
        desc.setObjectName("PageSubtitle")
        desc.setWordWrap(True)
        left.addWidget(title)
        left.addWidget(desc)
        btn_row = QHBoxLayout()
        btn_physical = AnimatedButton(tr("edit_physical_keys"), accent="#EF4444")
        btn_physical.setObjectName("SaveBtn")
        btn_physical.setHoverHeights(52, 7)
        btn_physical.clicked.connect(lambda: self.switch_main_page(1))
        btn_screen = AnimatedButton(tr("screen_pages"), accent=self.config.get("accent_color", "#3B82F6"))
        btn_screen.setHoverHeights(52, 7)
        btn_screen.clicked.connect(lambda: self.switch_main_page(2))
        btn_row.addWidget(btn_physical)
        btn_row.addWidget(btn_screen)
        btn_row.addStretch()
        left.addSpacing(12)
        left.addLayout(btn_row)
        left.addStretch()
        hero_l.addLayout(left, 2)

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
            self.log_area.append(f"✓ {msg}")

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
        self.lbl_current_assignment.setText(f"{tr('current_assign')} {cfg.get('name', tr('empty'))}")
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
        self.config["buttons"][self.current_signal] = {"name": action_name, "action": action_data}
        save_config(self.config)
        self.lbl_current_assignment.setText(f"{tr('current_assign')} {action_name}")
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
        for i, btn in enumerate(self.screen_btns):
            if page == 1 and i == 7: btn.setText(tr("btn_next")); btn.setStyleSheet("background-color: #1E293B; color: #64748B;"); continue
            elif page in [2, 3, 4] and i == 4: btn.setText(tr("btn_prev")); btn.setStyleSheet("background-color: #1E293B; color: #64748B;"); continue
            elif page in [2, 3, 4] and i == 7: btn.setText(tr("btn_next")); btn.setStyleSheet("background-color: #1E293B; color: #64748B;"); continue
            btn.setStyleSheet("")
            sig = f"NEX:P{page}_B{i+1}"
            cfg = self.config.get("buttons", {}).get(sig, {})
            if page >= 3 and cfg.get("btn_text"): btn.setText(f"{cfg.get('btn_text')}\n({cfg.get('name', tr('empty'))})")
            else: btn.setText(f"{tr('button_label').format(i+1)}\n({cfg.get('name', tr('empty'))})")

    def on_screen_btn_clicked(self, idx):
        page = self.combo_page.currentIndex() + 1
        if page == 1 and idx == 7: self.combo_page.setCurrentIndex(1); return
        if page in [2, 3, 4] and idx == 4: self.combo_page.setCurrentIndex(page - 2); return
        if page in [2, 3] and idx == 7: self.combo_page.setCurrentIndex(page); return
        if page == 4 and idx == 7: return
        
        self.current_screen_signal = f"NEX:P{page}_B{idx+1}"
        self.lbl_screen_selected.setText(f"{tr('screen_selected')} {tr('page_label').format(page)} - {tr('button_label').format(idx+1)}")
        cfg = self.config.get("buttons", {}).get(self.current_screen_signal, {})
        self.input_btn_text.setText(cfg.get("btn_text", ""))
        
        if page < 3: self.input_btn_text.setEnabled(False); self.input_btn_text.setPlaceholderText(tr("placeholder_readonly"))
        else: self.input_btn_text.setEnabled(True); self.input_btn_text.setPlaceholderText(tr("placeholder_text"))
            
        if cfg.get("action"):
            act = cfg["action"]
            if act.get("type") in ["custom_web", "web"]:
                idx_b = self.combo_browser_scr.findData(act.get("browser", "default"))
                if idx_b >= 0: self.combo_browser_scr.setCurrentIndex(idx_b)
            if act.get("type") == "custom_app":
                idx_a = self.combo_app_act_scr.findData(act.get("app_action", "open"))
                if idx_a >= 0: self.combo_app_act_scr.setCurrentIndex(idx_a)
            
        self.screen_macro_panel.setEnabled(True)

    def save_screen_macro(self):
        cat = self.combo_screen_cat.currentText()
        if cat == tr("no_action"): self.config["buttons"].pop(self.current_screen_signal, None)
        else:
            action_data = self.combo_screen_act.currentData()
            if action_data: action_data = action_data.copy()
            action_name = self.combo_screen_act.currentText()
            btn_text = self.input_btn_text.text().strip()
            page = self.combo_page.currentIndex() + 1
            
            if action_data and action_data.get("type") in ["custom_web", "custom_app", "custom_hotkey", "type_text"]: action_data["custom_arg"] = self.input_screen_custom.text().strip()
            if action_data and action_data.get("type") in ["custom_web", "web"]: action_data["browser"] = ["default", "chrome", "edge", "firefox"][self.combo_browser_scr.currentIndex()]
            if action_data and action_data.get("type") == "custom_app": action_data["app_action"] = ["open", "close", "force_close"][self.combo_app_act_scr.currentIndex()]
            
            if "buttons" not in self.config: self.config["buttons"] = {}
            self.config["buttons"][self.current_screen_signal] = {"name": action_name, "action": action_data, "btn_text": btn_text}
            
            if page >= 3 and self.serial_thread and self.serial_thread.is_running:
                if page in NEXTION_OBJ_MAP:
                    nextion_page = f"page{page}"
                    btn_idx = int(self.current_screen_signal.split("_")[1][1:]) - 1
                    obj_name = NEXTION_OBJ_MAP[page][btn_idx]
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
        l_sys.addWidget(self.chk_startup)
        l_sys.addWidget(self.chk_bg)
        s_layout.addWidget(group_sys)

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

        middle_row = QHBoxLayout()
        middle_row.setSpacing(18)

        group_mobile = HoverScaleFrame(grow_by=8)
        group_mobile.setObjectName("GlassCard")
        group_mobile.setHoverHeights(250, 10)
        l_mobile = QVBoxLayout(group_mobile)
        l_mobile.setContentsMargins(20, 20, 20, 20)
        l_mobile.setSpacing(12)
        lbl_mobile_title = QLabel(tr("tab_web"))
        lbl_mobile_title.setObjectName("SectionTitle")
        l_mobile.addWidget(lbl_mobile_title)
        mobile_layout = QHBoxLayout()
        self.btn_mobile = AnimatedButton(tr("mobile_server"), accent=lambda: self.current_accent())
        self.btn_mobile.setHoverHeights(46, 6)
        self.btn_mobile.clicked.connect(self.toggle_mobile_server)
        mobile_layout.addWidget(self.btn_mobile)

        self.btn_qr = AnimatedButton(tr("toggle_qr"), accent=lambda: self.current_accent())
        self.btn_qr.setHoverHeights(46, 6)
        self.btn_qr.clicked.connect(self.toggle_qr)
        self.btn_qr.setVisible(False)
        mobile_layout.addWidget(self.btn_qr)

        self.lbl_mobile_ip = QLabel("")
        self.lbl_mobile_ip.setStyleSheet("color: #10B981; font-weight: bold; font-size: 14px;")
        mobile_layout.addWidget(self.lbl_mobile_ip)
        mobile_layout.addStretch()
        l_mobile.addLayout(mobile_layout)

        self.lbl_qr_image = QLabel()
        self.lbl_qr_image.setFixedSize(150, 150)
        self.lbl_qr_image.setScaledContents(True)
        self.lbl_qr_image.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.lbl_qr_image.setVisible(False)
        l_mobile.addWidget(self.lbl_qr_image, alignment=Qt.AlignLeft)

        self.lbl_web_url = QLabel("")
        self.lbl_web_url.setWordWrap(True)
        self.lbl_web_url.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_web_url.setObjectName("Muted")
        self.lbl_web_url.setVisible(False)
        self.lbl_web_url.setMaximumHeight(0)
        l_mobile.addWidget(self.lbl_web_url)

        self.btn_copy_web_url = AnimatedButton(tr("copy_web_url"), accent=lambda: self.current_accent())
        self.btn_copy_web_url.setHoverHeights(42, 5)
        self.btn_copy_web_url.clicked.connect(self.copy_web_url)
        self.btn_copy_web_url.setVisible(False)
        l_mobile.addWidget(self.btn_copy_web_url)

        l_mobile.addStretch()
        middle_row.addWidget(group_mobile, 3)

        roadmap_card = HoverScaleFrame(grow_by=8)
        roadmap_card.setObjectName("GlassCard")
        roadmap_card.setHoverHeights(250, 10)
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
        middle_row.addWidget(roadmap_card, 2)

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

    def copy_web_url(self):
        url = self.config.get("mobile_url", "")
        if url:
            QApplication.clipboard().setText(url)
            self.show_saved_feedback(tr("web_url_copied"))

    def toggle_mobile_server(self):
        if self.mobile_thread and self.mobile_thread.is_running:
            self.mobile_thread.stop()
            self.mobile_thread = None
            self.btn_mobile.setText(tr("mobile_server"))
            self.lbl_mobile_ip.setText("")
            self.btn_qr.setVisible(False)
            self.lbl_qr_image.setVisible(False)
            if hasattr(self, "lbl_web_url"):
                self.lbl_web_url.setVisible(False)
                self.lbl_web_url.setText("")
            if hasattr(self, "btn_copy_web_url"):
                self.btn_copy_web_url.setVisible(False)
        else:
            alphabet = string.ascii_uppercase + string.digits
            new_pin = ''.join(secrets.choice(alphabet) for _ in range(6))
            self.config["mobile_pin"] = new_pin
            token = secrets.token_urlsafe(8)
            self.config["web_token"] = token
            save_config(self.config)
            
            self.mobile_thread = MobileServerThread()
            self.mobile_thread.start()
            self.btn_mobile.setText(tr("mobile_stop"))
            ip = get_local_ip()
            url = f"http://{ip}:45729/{token}?pin={new_pin}"
            self.config["mobile_url"] = url
            save_config(self.config)
            if hasattr(self, "lbl_web_url"):
                self.lbl_web_url.setText("")
                self.lbl_web_url.setVisible(False)
            if hasattr(self, "btn_copy_web_url"):
                self.btn_copy_web_url.setVisible(True)
            self.lbl_mobile_ip.setText(tr("pin_code").format(new_pin))
            
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

    def toggle_qr(self):
        show = not self.lbl_qr_image.isVisible()
        self.lbl_qr_image.setVisible(show)
        if hasattr(self, "lbl_web_url"):
            self.lbl_web_url.setVisible(False)
        if hasattr(self, "btn_copy_web_url"):
            self.btn_copy_web_url.setVisible(show)

    def change_language(self):
        new_lang = self.combo_lang.currentData()
        if new_lang != self.config.get("language", "tr"):
            self.config["language"] = new_lang
            save_config(self.config)
            self.restart_app()

    def factory_reset(self):
        cevap = QMessageBox.question(self, tr("confirm"), tr("reset_confirm"), QMessageBox.Yes | QMessageBox.No)
        if cevap == QMessageBox.Yes:
            self.config["buttons"] = FACTORY_DEFAULT_BUTTONS.copy()
            save_config(self.config)
            self.restart_app()

    def restart_app(self):
        save_config(self.config)
        if self.serial_thread: self.serial_thread.stop()
        if self.mobile_thread: self.mobile_thread.stop()
        QApplication.quit()
        subprocess.Popen([sys.executable] + sys.argv)

    def refresh_ports(self):
        self.port_combo.clear()
        ALLOWED_VIDS =["2341", "1A86", "0403", "10C4"] 
        found = False
        for p in serial.tools.list_ports.comports():
            vid = f"{p.vid:04X}".upper() if p.vid else ""
            if vid in ALLOWED_VIDS or "Arduino" in (p.description or ""):
                self.port_combo.addItem("NexDeck", p.device)
                found = True
        if not found: self.port_combo.addItem(tr("device_not_found"), None)
        elif self.config.get("last_port"):
            idx = self.port_combo.findData(self.config["last_port"])
            if idx >= 0: self.port_combo.setCurrentIndex(idx)

    def toggle_connection(self):
        if self.serial_thread and self.serial_thread.is_running:
            self.serial_thread.stop()
            self.serial_thread = None
            self.btn_connect.setText(tr("connect"))
            self.btn_connect.setObjectName("ConnectBtn")
            self.btn_connect.style().unpolish(self.btn_connect); self.btn_connect.style().polish(self.btn_connect)
            if hasattr(self, "lbl_sidebar_status"):
                self.lbl_sidebar_status.setText(tr("status_waiting"))
                self.lbl_sidebar_status.setStyleSheet("color: #94A3B8; background-color: #111827; border: 1px solid #263244; border-radius: 16px; padding: 8px 12px; font-size: 12px; font-weight: 800;")
            if MAIN_WINDOW: MAIN_WINDOW.log_area.append(f"[-] {tr('disconnect')}")
        else:
            port = self.port_combo.currentData()
            if port:
                self.config["last_port"] = port
                save_config(self.config)
                self.serial_thread = SerialThread(port)
                self.serial_thread.data_received.connect(self.handle_serial_data)
                self.serial_thread.start()
                self.btn_connect.setText(tr("disconnect"))
                self.btn_connect.setObjectName("DisconnectBtn")
                self.btn_connect.style().unpolish(self.btn_connect); self.btn_connect.style().polish(self.btn_connect)
                if hasattr(self, "lbl_sidebar_status"):
                    self.lbl_sidebar_status.setText(tr("status_connected"))
                    self.lbl_sidebar_status.setStyleSheet("color: #22C55E; background-color: #052E1A; border: 1px solid #14532D; border-radius: 16px; padding: 8px 12px; font-size: 12px; font-weight: 900;")
                if MAIN_WINDOW: MAIN_WINDOW.log_area.append(tr("connected_log"))
                QTimer.singleShot(2500, self.sync_nextion_texts)

    def sync_nextion_texts(self):
        if not self.serial_thread or not self.serial_thread.is_running: return
        for sig, cfg in self.config.get("buttons", {}).items():
            if sig.startswith("NEX:P3_") or sig.startswith("NEX:P4_"):
                page_num = int(sig.split("_")[0][-1])
                btn_idx = int(sig.split("_")[1][1:]) - 1
                btn_text = cfg.get("btn_text", "")
                if btn_text and page_num in NEXTION_OBJ_MAP:
                    nextion_page = f"page{page_num}"
                    obj_name = NEXTION_OBJ_MAP[page_num][btn_idx]
                    cmd = f'NEXCMD:{nextion_page}.{obj_name}.txt="{btn_text}"\n'
                    self.serial_thread.send_data(cmd)
                    time.sleep(0.05)

    def handle_serial_data(self, data):
        if MAIN_WINDOW: MAIN_WINDOW.log_area.append(f"{tr('log_signal')} {data}")
        
        if data in ["ENC:UP", "ENC:DOWN"]:
            # Hızlı çevirmede gelen seri sinyalleri tek tek uygulamak yerine
            # kısa bir tamponda topluyoruz. Bu, yukarı/aşağı zıplamayı ve
            # Windows ses karıştırıcısının kararsız tepki vermesini azaltır.
            self.encoder_pending_steps += 1 if data == "ENC:UP" else -1
            if not self.encoder_flush_timer.isActive():
                self.encoder_flush_timer.start(35)
            return

        cfg = self.config.get("buttons", {}).get(data)
        if cfg and cfg.get("action"):
            if MAIN_WINDOW: MAIN_WINDOW.log_area.append(tr("found_task").format(cfg.get("name")))
            execute_macro(cfg["action"])
        else:
            if MAIN_WINDOW: MAIN_WINDOW.log_area.append(tr("no_assigned_task"))

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
            MAIN_WINDOW.log_area.append(tr("audio_apps_refresh_log"))

    def save_encoder_value(self, value, text=""):
        if value in ["__disabled_header__", "__no_audio_apps__", None]:
            return False
        if "encoder" not in self.config:
            self.config["encoder"] = {}
        self.config["encoder"]["turn"] = value
        save_config(self.config)
        if text and MAIN_WINDOW:
            MAIN_WINDOW.log_area.append(tr("encoder_changed_log").format(text))
        return True

    def process_encoder_pending_steps(self):
        steps = self.encoder_pending_steps
        self.encoder_pending_steps = 0
        if steps == 0:
            return

        enc_cfg = self.config.get("encoder", {})
        turn_action = enc_cfg.get("turn", "general_volume")
        delta = max(-0.20, min(0.20, steps * 0.01))  # her kademe %1, tek pakette en fazla %20

        if turn_action in ["general_volume", "Genel Ses Seviyesi", "General Volume"]:
            self.change_master_volume(delta)
        elif turn_action in ["brightness", "Ekran Parlaklığı", "Screen Brightness"]:
            brightness_delta = max(-20, min(20, steps))
            execute_macro({"type": "nircmd", "cmd": f"changebrightness {brightness_delta}"})
        else:
            self.change_app_volume(turn_action, delta)

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
                    MAIN_WINDOW.log_area.append(tr("master_volume_fallback").format(str(e)))
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
                MAIN_WINDOW.log_area.append(tr("audio_session_not_found"))

        except Exception as e:
            if MAIN_WINDOW:
                MAIN_WINDOW.log_area.append(tr("volume_error").format(str(e)))
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

    def toggle_bg(self):
        self.config["run_in_bg"] = not self.config.get("run_in_bg", False)
        self.chk_bg.setText("✅ " + tr("run_bg") if self.config.get("run_in_bg") else "❌ " + tr("run_bg"))
        save_config(self.config)

    def apply_startup_setting(self):
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "NexStudio"
        exe_path = sys.argv[0]
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            if self.config.get("start_with_win"): winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{exe_path}"')
            else:
                try: winreg.DeleteValue(key, app_name)
                except: pass
            winreg.CloseKey(key)
        except Exception as e: print(tr("startup_error"), e)

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        pixmap = QPixmap(32, 32); pixmap.fill(QColor(self.current_accent()))
        self.tray_icon.setIcon(QIcon(pixmap))
        tray_menu = QMenu()
        tray_menu.addAction(QAction(tr("tray_show"), self, triggered=self.show))
        tray_menu.addAction(QAction(tr("tray_exit"), self, triggered=self.force_quit))
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(lambda r: self.show() if r == QSystemTrayIcon.DoubleClick else None)
        self.tray_icon.show()

    def closeEvent(self, event):
        if self.config.get("run_in_bg"):
            event.ignore(); self.hide()
            self.tray_icon.showMessage("NexStudio", tr("running_bg"), QSystemTrayIcon.Information, 2000)
        else: self.force_quit()

    def force_quit(self):
        if self.serial_thread: self.serial_thread.stop()
        if self.mobile_thread: self.mobile_thread.stop()
        QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    try: 
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('nexstudio.pro.version.1')
    except: 
        pass
    
    app.setStyle("Fusion")
    app.setWindowIcon(QIcon(get_resource_path("app_icon.ico")))
    
    MAIN_WINDOW = NexHubApp()
    MAIN_WINDOW.show()
    
    sys.exit(app.exec_())

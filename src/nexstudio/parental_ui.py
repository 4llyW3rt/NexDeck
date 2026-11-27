"""
2.8.0: Ebeveyn kontrolü — kilit ekranı ve bekçi (Qt ana iş parçacığında çalışır).

Her saniye: durum kontrol edilir, kilitli değilse kullanım sayılır.
- Süreye 'warn_min' kala tepsiden uyarı (kaydetmeleri için).
- Süre dolunca / izinli saat dışında / saat oynanınca: her ekranı kaplayan, en üstte duran kilit penceresi;
  kullanıcının pencereli programları kapatılır (NexStudio ve Windows klasöründeki sistem işlemleri hariç), kilit boyunca
  yenisi açılamaz; Win, Alt+Tab, Ctrl+Esc, Ctrl+Shift+Esc tuşları engellenir.
- Kilitte: ebeveyn şifresiyle ek süre ya da 30 dk yönetici oturumu. (2.8.1: Telegram ile uzaktan ek süre isteği.)
- Windows kilitlenince (Win+L) yönetici oturumu biter.
Deneme modu (NEXSTUDIO_PARENTAL_DRYRUN=1, yalnızca kaynaktan): en üste sabitlenmez, program kapatılmaz, tuş engellenmez.
"""
import ctypes
import os
import sys
import time
from ctypes import wintypes

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (QApplication, QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QSystemTrayIcon, QVBoxLayout, QWidget)

from . import parental
from .core import ui_log
from .i18n import ui_tr

# Kilitte kapatılmayan Windows kabuk/sistem işlemleri: yalnızca Windows klasöründen çalışıyorlarsa (ad taklidi geçmez)
SYSTEM_EXES = {
    "explorer.exe", "dwm.exe", "csrss.exe", "winlogon.exe", "logonui.exe", "lockapp.exe", "shellexperiencehost.exe",
    "startmenuexperiencehost.exe", "searchhost.exe", "searchapp.exe", "textinputhost.exe", "ctfmon.exe", "sihost.exe",
    "fontdrvhost.exe", "runtimebroker.exe", "dllhost.exe", "taskhostw.exe", "smartscreen.exe", "applicationframehost.exe",
}
WIN_DIR = os.path.normcase(os.environ.get("SystemRoot", r"C:\Windows")) + os.sep
TEXTS = {
    "limit": ("Bugünkü süren doldu", "Günlük kullanım süresi bitti. Ek süre için ebeveynine sor."),
    "hours": ("Şu an kullanım saatleri dışında", "Bilgisayar {0} – {1} arasında kullanılabilir."),
    "clock": ("Bilgisayarın saati değiştirildi", "Ebeveyn şifresi girilene kadar bilgisayar kilitli."),
}
CLOCK_JUMP = 120   # sn: duvar saati ile monotonik saat arasındaki fark bundan çok değişirse saat oynanmış sayılır

user32 = ctypes.windll.user32


def _top_windows():
    """(hwnd, pid) — görünür, ya başlığı olan ya da büyük (oyunlar, başlıksız pencereler) üst düzey pencereler."""
    out = []
    proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            r = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(r))
            big = (r.right - r.left) >= 300 and (r.bottom - r.top) >= 200
            if user32.GetWindowTextLengthW(hwnd) > 0 or big:
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                out.append((hwnd, pid.value))
        return True
    user32.EnumWindows(proc(cb), 0)
    return out


def _child_pids(hwnd):
    """UWP (Mağaza) uygulamaları ApplicationFrameHost içinde: asıl uygulamanın işlemi alt pencerede."""
    pids = set()
    proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(child, _):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(child, ctypes.byref(pid))
        pids.add(pid.value)
        return True
    user32.EnumChildWindows(hwnd, proc(cb), 0)
    return pids


def windows_session_locked():
    """Win+L ile kilitlenmiş oturumda giriş masaüstüne geçilemez (anlık kontrol, yalnızca bu oturum)."""
    try:
        h = user32.OpenInputDesktop(0, False, 0x0100)   # DESKTOP_SWITCHDESKTOP
        if not h:
            return True
        ok = user32.SwitchDesktop(h)
        user32.CloseDesktop(h)
        return not ok
    except Exception:
        return False


class KeyBlocker:
    """Kilitliyken Win, Alt+Tab, Alt+Esc, Ctrl+Esc, Ctrl+Shift+Esc tuşlarını engelleyen düşük seviye klavye kancası."""
    WH_KEYBOARD_LL, VK_TAB, VK_ESCAPE, VK_LWIN, VK_RWIN, VK_CONTROL, VK_SHIFT = 13, 0x09, 0x1B, 0x5B, 0x5C, 0x11, 0x10
    LLKHF_ALTDOWN = 0x20

    class KBD(ctypes.Structure):
        _fields_ = [("vkCode", wintypes.DWORD), ("scanCode", wintypes.DWORD), ("flags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]

    def __init__(self):
        self.hook = None
        self.proc_t = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
        self.proc = self.proc_t(self._cb)
        user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
        user32.CallNextHookEx.restype = ctypes.c_ssize_t
        user32.SetWindowsHookExW.restype = wintypes.HHOOK

    def _cb(self, code, wparam, lparam):
        try:
            if code == 0:
                k = ctypes.cast(lparam, ctypes.POINTER(self.KBD)).contents
                alt = bool(k.flags & self.LLKHF_ALTDOWN)
                ctrl = bool(user32.GetAsyncKeyState(self.VK_CONTROL) & 0x8000)
                if k.vkCode in (self.VK_LWIN, self.VK_RWIN) or (alt and k.vkCode in (self.VK_TAB, self.VK_ESCAPE)) \
                        or (ctrl and k.vkCode == self.VK_ESCAPE):
                    return 1   # tuşu yut
        except Exception:
            pass
        return user32.CallNextHookEx(None, code, wparam, lparam)

    def start(self):
        if self.hook or parental.DRY_RUN:
            return
        self.hook = user32.SetWindowsHookExW(self.WH_KEYBOARD_LL, self.proc, None, 0)

    def stop(self):
        if self.hook:
            user32.UnhookWindowsHookEx(self.hook)
            self.hook = None


class LockWindow(QWidget):
    """Bir ekranı kaplayan kilit penceresi."""

    def __init__(self, guard, screen):
        flags = Qt.FramelessWindowHint | Qt.Tool
        if not parental.DRY_RUN:
            flags |= Qt.WindowStaysOnTopHint
        super().__init__(None, flags)
        self.guard = guard
        self.screen_name = screen.name()
        self.setStyleSheet("QWidget{background:#0F1218;color:#E8ECF3;font-family:'Segoe UI';}"
                           "QPushButton{background:#F2601C;color:#fff;border:0;border-radius:10px;padding:10px 18px;font-size:15px;}"
                           "QPushButton#ghost{background:#232836;} QPushButton:disabled{background:#3A4050;}"
                           "QLineEdit,QComboBox{background:#1A1F29;border:1px solid #2C3343;"
                           "border-radius:8px;padding:8px;font-size:15px;color:#E8ECF3;}")
        self.setGeometry(screen.geometry())
        box = QVBoxLayout(self)
        box.setAlignment(Qt.AlignCenter)
        self.title = QLabel(); self.title.setStyleSheet("font-size:34px;font-weight:600;")
        self.text = QLabel(); self.text.setStyleSheet("font-size:17px;color:#9AA3B5;")
        self.info = QLabel(); self.info.setStyleSheet("font-size:14px;color:#F2601C;")
        for w in (self.title, self.text, self.info):
            w.setAlignment(Qt.AlignCenter)
            box.addWidget(w)
        box.addSpacing(24)
        row = QHBoxLayout()
        self.pw = QLineEdit(); self.pw.setEchoMode(QLineEdit.Password); self.pw.setPlaceholderText(ui_tr("Ebeveyn şifresi"))
        self.pw.setFixedWidth(240)
        self.minutes = QComboBox()
        for m in (15, 30, 60, 120):
            self.minutes.addItem(ui_tr("+{0} dk", m), m)
        self.btn_extra = QPushButton(ui_tr("Ek süre ver"))
        self.btn_admin = QPushButton(ui_tr("Yönetici oturumu")); self.btn_admin.setObjectName("ghost")
        # 2.8.1: Telegram'dan ebeveyne ek süre isteği
        self.btn_request = QPushButton(ui_tr("📩 Ebeveynden ek süre iste"))
        self.btn_request.clicked.connect(self._request)
        row.addStretch(1)
        for w in (self.pw, self.minutes, self.btn_extra, self.btn_admin):
            row.addWidget(w)
        row.addStretch(1)
        box.addLayout(row)
        self.msg = QLabel(); self.msg.setAlignment(Qt.AlignCenter); self.msg.setStyleSheet("color:#E5484D;font-size:14px;")
        box.addWidget(self.msg)
        box.addSpacing(18)
        req_row = QHBoxLayout(); req_row.addStretch(1); req_row.addWidget(self.btn_request); req_row.addStretch(1)
        box.addLayout(req_row)
        self.req_info = QLabel(); self.req_info.setAlignment(Qt.AlignCenter); self.req_info.setStyleSheet("color:#9AA3B5;font-size:14px;")
        box.addWidget(self.req_info)
        self.btn_extra.clicked.connect(lambda: self._unlock(extra=True))
        self.btn_admin.clicked.connect(lambda: self._unlock(extra=False))
        # Enter: ek süre görünüyorsa ek süre, değilse (saat dışı / saat oynandı) yönetici oturumu
        self.pw.returnPressed.connect(lambda: self._unlock(extra=self.btn_extra.isVisible()))

    def _set_enabled(self, on):
        for w in (self.pw, self.btn_extra, self.btn_admin):
            w.setEnabled(on)

    def _unlock(self, extra):
        try:
            ok = parental.check_password(self.pw.text())
        except PermissionError as e:   # çok fazla yanlış deneme
            self.pw.clear(); self.msg.setText(ui_tr(str(e)))
            return
        if not ok:
            self.pw.clear()
            self.msg.setText(ui_tr("Şifre yanlış"))
            self._set_enabled(False)   # arayüzü dondurmadan kısa bekleme
            QTimer.singleShot(800, lambda: self._set_enabled(True))
            return
        self.pw.clear(); self.msg.clear()
        if extra:
            parental.grant_extra(self.minutes.currentData())
            ui_log(f"👪 Ebeveyn ek süre verdi: +{self.minutes.currentData()} dk")
        else:
            parental.start_admin()
            ui_log("👪 Ebeveyn yönetici oturumu açtı (30 dk)")
        self.guard.tick()

    def _request(self):
        import threading
        from . import telegram
        self.btn_request.setEnabled(False)

        def run():
            try:
                telegram.request_extra()
            except Exception as e:
                self.guard.req_error = (ui_tr(str(e)), time.monotonic() + 6)
        threading.Thread(target=run, daemon=True).start()

    def update_texts(self, st):
        title, text = TEXTS.get(st["reason"], TEXTS["limit"])
        self.title.setText(ui_tr(title))
        self.text.setText(ui_tr(text, st.get("start") or "", st.get("end") or ""))
        self.info.setText(ui_tr("Bugün kullanılan: {0} dk", st["used_min"]) + ("   ·   " + ui_tr("DENEME MODU") if st.get("dry_run") else ""))
        # saat dışında / saat oynanınca ek süre verilmez, sadece yönetici oturumu
        self.minutes.setVisible(st["reason"] == "limit")
        self.btn_extra.setVisible(st["reason"] == "limit")
        from . import telegram
        can_request = st["reason"] == "limit" and telegram.paired()
        req = telegram.request_state()
        self.btn_request.setVisible(can_request)
        self.btn_request.setEnabled(req["state"] != "pending")
        self.req_info.setVisible(can_request)
        err, until = getattr(self.guard, "req_error", ("", 0))
        self.req_info.setText(err if err and time.monotonic() < until else
                              {"pending": ui_tr("İstek gönderildi, ebeveynin cevabı bekleniyor…"),
                               "denied": ui_tr("Ebeveynin isteği reddetti.")}.get(req["state"], ""))

    def keyPressEvent(self, e):
        if parental.DRY_RUN and e.key() == Qt.Key_Escape:
            self.guard.hide_lock()   # deneme modunda Esc kapatır
            return
        super().keyPressEvent(e)

    def closeEvent(self, e):
        if self.guard.locked and not parental.DRY_RUN:
            e.ignore()   # Alt+F4 ile kapatılamaz
        else:
            super().closeEvent(e)


class ParentalGuard:
    def __init__(self, app_window):
        self.app = app_window
        self.windows = []
        self.locked = False
        self.warned = None
        self.keys = KeyBlocker()
        self._last_flush = time.monotonic()
        self._clock_offset = time.time() - time.monotonic()
        from . import telegram
        telegram.start()   # 2.8.1: bot kurulu değilse boşta bekler
        self.timer = QTimer(app_window)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)

    def tick(self):
        try:
            self._check_clock()
            if parental.admin_left() and windows_session_locked():
                parental.end_admin()
                ui_log("👪 Windows kilitlendi: yönetici oturumu kapandı")
            st = parental.status()
            if not st["locked"]:
                parental.add_usage(1)   # kilitliyken süre sayılmaz
            if time.monotonic() - self._last_flush > 60:
                self._last_flush = time.monotonic()
                parental.flush()
            if st["locked"]:
                self.show_lock(st)
                self.enforce()
            elif self.locked:
                self.hide_lock()
            key = (time.strftime("%Y-%m-%d"), st["soonest_min"] is not None and st["soonest_min"] > 1)
            if st["warn"] and self.warned != key:
                self.warned = key
                self._notify(ui_tr("{0} dakika kaldı. İşini kaydet; süre bitince bilgisayar kilitlenecek.", st["soonest_min"]))
        except Exception as e:  # bekçi asla çökmesin
            ui_log(f"⚠️ Ebeveyn kontrolü hatası: {e}")

    def _check_clock(self):
        """Windows saati/tarihi ileri-geri alınırsa (süreyi sıfırlamak için) kilit."""
        offset = time.time() - time.monotonic()
        if abs(offset - self._clock_offset) > CLOCK_JUMP:
            ui_log(f"👪 Bilgisayarın saati değişti ({int(offset - self._clock_offset)} sn)")
            parental.set_tamper()
        self._clock_offset = offset

    def _notify(self, text):
        tray = getattr(self.app, "tray_icon", None)
        if tray is not None:
            tray.showMessage("NexStudio · " + ui_tr("Ebeveyn kontrolü"), text, QSystemTrayIcon.Warning, 8000)
        ui_log("👪 " + text)

    def show_lock(self, st):
        screens = QApplication.screens()
        if self.locked and sorted(w.screen_name for w in self.windows) != sorted(s.name() for s in screens):
            self._close_windows()   # ekran takıldı/çıkarıldı: pencereler yeniden kurulur
        if not self.locked:
            self.locked = True
            ui_log(f"👪 Kilit: {st['reason']} (bugün {st['used_min']} dk)")
            self.keys.start()
            self.enforce(first=True)
        if not self.windows:
            self.windows = [LockWindow(self, s) for s in screens]
        for w in self.windows:
            w.update_texts(st)
            if not w.isVisible() or w.isMinimized():
                w.showNormal()
            if not parental.DRY_RUN:
                w.raise_(); w.activateWindow()

    def _close_windows(self):
        for w in self.windows:
            w.hide(); w.deleteLater()
        self.windows = []

    def hide_lock(self):
        self.locked = False
        from . import telegram
        telegram.clear_answered()
        self.keys.stop()
        self._close_windows()
        ui_log("👪 Kilit kalktı")

    def _keep_pids(self):
        import psutil
        me = os.getpid()
        keep = {me}
        try:
            keep |= {p.pid for p in psutil.Process(me).children(recursive=True)}
            keep.add(psutil.Process(me).ppid())
        except Exception:
            pass
        return keep

    def _is_safe(self, p):
        try:
            exe = os.path.normcase(p.exe())
        except Exception:
            return True   # erişilemeyen (başka kullanıcı/sistem) işlem: dokunma
        name = os.path.basename(exe)
        if name in SYSTEM_EXES and exe.startswith(WIN_DIR):
            return True
        own = os.path.normcase(os.path.dirname(sys.executable)) + os.sep
        return getattr(sys, "frozen", False) and exe.startswith(own)   # kendi kurulum klasörümüz

    def enforce(self, first=False):
        """Kilitteyken kullanıcının pencereli programlarını kapatır."""
        try:
            import psutil
        except ImportError:
            return
        keep = self._keep_pids()
        targets = set()
        for hwnd, pid in _top_windows():
            targets.add(pid)
            targets |= _child_pids(hwnd)   # UWP uygulamaları (ApplicationFrameHost içindekiler)
        for pid in targets - keep:
            try:
                p = psutil.Process(pid)
                if self._is_safe(p):
                    continue
                name = p.name()
                if parental.DRY_RUN:
                    if first:
                        ui_log(f"👪 [deneme] kapatılırdı: {name}")
                    continue
                p.kill()
                ui_log(f"👪 Kilitte kapatıldı: {name}")
            except Exception:
                continue

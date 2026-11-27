"""
2.8.0: Ebeveyn kontrolü (çekirdek mantık, arayüzsüz).

- Ebeveyn şifresi (PBKDF2) ve tek seferlik gösterilen kurtarma kodu
- Günlük kullanım süresi ve izinli saat aralığı; süre bitince kilit
- 30 dakikalık "yönetici oturumu": ebeveyn şifreyle açar, süre sayılmaz, kilit uygulanmaz
- Kullanım sadece bilgisayar başında biri varken sayılır (2 dk'dan uzun boşta kalınca sayaç durur)

Ayarlar config.json > "parental" altında. Kilit penceresi ve program kapatma classic_app.ParentalGuard'da.
Deneme modu: NEXSTUDIO_PARENTAL_DRYRUN=1 -> kilit penceresi en üste sabitlenmez, hiçbir program kapatılmaz.
"""
import ctypes
import hashlib
import hmac
import os
import secrets
import sys
import threading
import time
from datetime import datetime, timedelta

from . import state
from .core import CONFIG_LOCK
from .engine import save_config

ADMIN_MINUTES = 30
IDLE_LIMIT = 120          # sn: bundan uzun boşta kalınırsa süre sayılmaz
DEFAULTS = {"enabled": False, "pw": "", "recovery": "", "daily_min": 120, "start": "07:00", "end": "22:00",
            "warn_min": 5, "usage": {}, "extra": {}}
# Deneme modu yalnızca kaynaktan çalışırken (kurulu exe'de ortam değişkeniyle kapatılamaz)
DRY_RUN = os.environ.get("NEXSTUDIO_PARENTAL_DRYRUN") == "1" and not getattr(sys, "frozen", False)
FAIL_LIMIT, FAIL_COOLDOWN = 5, 60   # 5 yanlış şifre -> 60 sn bekleme

_admin_until = 0.0        # time.monotonic() tabanlı: Windows saatini geri almak oturumu uzatmaz
_lock = threading.RLock()
_fails = []               # yanlış şifre zamanları (monotonic)
_tamper = False           # saat oynandı: ebeveyn açana kadar kilit


def cfg():
    with CONFIG_LOCK:
        p = state.APP_CONFIG.setdefault("parental", {})
        for k, v in DEFAULTS.items():
            p.setdefault(k, v if not isinstance(v, dict) else {})
        return p


def _save():
    save_config(state.APP_CONFIG)


# ----- şifre ve kurtarma kodu -----
def _hash(secret, salt=None):
    salt = salt or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), bytes.fromhex(salt), 200_000).hex()
    return f"{salt}${h}"


def _verify(secret, stored):
    try:
        salt, _ = stored.split("$", 1)
    except (AttributeError, ValueError):
        return False
    return hmac.compare_digest(_hash(secret, salt), stored)


def is_setup():
    return bool(cfg().get("pw"))


def _new_recovery():
    code = "-".join(secrets.token_hex(2).upper() for _ in range(4))   # ör. 3F9A-0C21-B7E4-55D0
    cfg()["recovery"] = _hash(code.replace("-", ""))
    return code


def setup(password):
    """İlk kurulum: şifre belirlenir, kurtarma kodu üretilir (yalnızca bir kez gösterilir)."""
    if is_setup():
        raise PermissionError("Ebeveyn şifresi zaten belirlenmiş")
    _check_strength(password)
    with CONFIG_LOCK:
        cfg()["pw"] = _hash(password)
        code = _new_recovery()
        _save()
    start_admin()
    return code


def _check_strength(password):
    if not isinstance(password, str) or len(password) < 6:
        raise ValueError("Şifre en az 6 karakter olmalı")


def cooldown_left():
    now = time.monotonic()
    with _lock:
        _fails[:] = [t for t in _fails if now - t < FAIL_COOLDOWN]
        return int(FAIL_COOLDOWN - (now - _fails[0])) + 1 if len(_fails) >= FAIL_LIMIT else 0


def _fail():
    with _lock:
        _fails.append(time.monotonic())


def check_password(password):
    """Yanlış denemeler sayılır; 5 yanlıştan sonra 60 sn hiçbir şifre kabul edilmez."""
    if cooldown_left():
        raise PermissionError(f"Çok fazla yanlış deneme. {cooldown_left()} sn bekle.")
    ok = isinstance(password, str) and _verify(password, cfg().get("pw", ""))
    if not ok:
        _fail()
    return ok


def reset_with_recovery(code, new_password):
    if cooldown_left():
        raise PermissionError(f"Çok fazla yanlış deneme. {cooldown_left()} sn bekle.")
    code = str(code or "").replace("-", "").replace(" ", "").upper()
    if not _verify(code, cfg().get("recovery", "")):
        _fail()
        raise PermissionError("Kurtarma kodu yanlış")
    _check_strength(new_password)
    with CONFIG_LOCK:
        cfg()["pw"] = _hash(new_password)
        new_code = _new_recovery()
        _save()
    start_admin()
    return new_code


def change_password(new_password):
    require_admin()
    _check_strength(new_password)
    with CONFIG_LOCK:
        cfg()["pw"] = _hash(new_password)
        _save()


def regenerate_recovery():
    require_admin()
    with CONFIG_LOCK:
        code = _new_recovery()
        _save()
    return code


# ----- yönetici oturumu -----
def start_admin(minutes=ADMIN_MINUTES):
    global _admin_until, _tamper
    with _lock:
        _admin_until = time.monotonic() + minutes * 60
        _tamper = False


def end_admin():
    global _admin_until
    with _lock:
        _admin_until = 0.0


def admin_left():
    return max(0, int(_admin_until - time.monotonic()))


def set_tamper():
    """Saat/tarih değişikliği algılandı: ebeveyn şifreyle açana kadar kilit."""
    global _tamper
    if cfg().get("enabled") and is_setup() and not admin_left():
        _tamper = True


def require_admin():
    if not admin_left():
        raise PermissionError("Önce ebeveyn şifresiyle yönetici oturumu aç")


# ----- süre -----
def _today(now=None):
    return (now or datetime.now()).strftime("%Y-%m-%d")


def _hm(text, fallback):
    try:
        h, m = str(text).split(":")
        return int(h) * 60 + int(m)
    except (ValueError, TypeError):
        return fallback


def idle_seconds():
    """Son klavye/fare hareketinden bu yana geçen süre (Windows)."""
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
    try:
        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(info)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            return 0.0
        k32 = ctypes.windll.kernel32
        k32.GetTickCount.restype = ctypes.c_uint   # işaretsiz: 24,8 günden uzun açık kalan bilgisayarda taşmasın
        return ((k32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000.0
    except Exception:
        return 0.0


def add_usage(seconds):
    """Her saniye çağrılır: biri bilgisayar başındaysa ve yönetici oturumu yoksa süre sayılır."""
    p = cfg()
    if not p.get("enabled") or admin_left() or idle_seconds() > IDLE_LIMIT or status()["reason"]:
        return   # kilitliyken (kilit ekranında) süre sayılmaz
    with CONFIG_LOCK:
        usage = p.setdefault("usage", {})
        day = _today()
        usage[day] = usage.get(day, 0) + seconds
        # eski günleri at (30 gün kalsın)
        for d in sorted(usage)[:-30]:
            usage.pop(d, None)


def flush():
    """Kullanım sayacını diske yazar (dakikada bir)."""
    if cfg().get("enabled"):
        with CONFIG_LOCK:
            _save()


def grant_extra(minutes):
    minutes = _int(minutes)
    if not 1 <= minutes <= 600:
        raise ValueError("Ek süre 1–600 dakika olmalı")
    with CONFIG_LOCK:
        extra = cfg().setdefault("extra", {})
        day = _today()
        extra[day] = int(extra.get(day, 0)) + int(minutes)
        for d in sorted(extra)[:-30]:
            extra.pop(d, None)
        _save()


def status(now=None):
    """Kilit durumu: {'enabled','setup','locked','reason','used_min','left_min','warn','admin_left', ...}"""
    p = cfg()
    now = now or datetime.now()
    day = _today(now)
    used = int(p.get("usage", {}).get(day, 0)) // 60
    extra = int(p.get("extra", {}).get(day, 0))
    limit = int(p.get("daily_min") or 0)
    left = (limit + extra - used) if limit else None
    minute = now.hour * 60 + now.minute
    start, end = _hm(p.get("start"), 0), _hm(p.get("end"), 24 * 60)
    if start == end:   # başlangıç = bitiş: saat sınırı yok
        in_hours, to_end = True, None
    else:
        in_hours = start <= minute < end if start < end else (minute >= start or minute < end)
        to_end = (end - minute) % (24 * 60) if in_hours else None
    reason = ""
    if p.get("enabled") and is_setup():
        if _tamper:
            reason = "clock"
        elif not in_hours:
            reason = "hours"
        elif left is not None and left <= 0:
            reason = "limit"
    soonest = min(x for x in (left, to_end) if x is not None) if (left is not None or to_end is not None) else None
    admin = admin_left()
    return {
        "enabled": bool(p.get("enabled")), "setup": is_setup(), "locked": bool(reason) and not admin,
        "reason": reason, "used_min": used, "extra_min": extra, "limit_min": limit,
        "left_min": None if left is None else max(0, left), "start": p.get("start"), "end": p.get("end"),
        "warn": bool(p.get("enabled")) and not reason and not admin and soonest is not None and 0 < soonest <= int(p.get("warn_min") or 5),
        "soonest_min": soonest, "admin_left": admin, "dry_run": DRY_RUN,
    }


def save_settings(values):
    require_admin()
    p = cfg()
    with CONFIG_LOCK:
        if "enabled" in values:
            if not isinstance(values["enabled"], bool):
                raise ValueError("Geçersiz ayar değeri")
            p["enabled"] = values["enabled"]
        if "daily_min" in values:
            p["daily_min"] = max(0, min(24 * 60, _int(values["daily_min"])))
        for key in ("start", "end"):
            if key in values:
                v = str(values[key])
                if not (len(v) == 5 and v[2] == ":" and v[:2].isdigit() and v[3:].isdigit() and int(v[:2]) < 24 and int(v[3:]) < 60):
                    raise ValueError("Saat SS:DD biçiminde olmalı")
                p[key] = v
        if "warn_min" in values:
            p["warn_min"] = max(1, min(30, _int(values["warn_min"])))
        _save()


def _int(v):
    """Tam sayı alanları: bool, sonsuz ve metin reddedilir."""
    if isinstance(v, bool):
        raise ValueError("Geçersiz süre")
    try:
        return int(v)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("Geçersiz süre")


def public_settings():
    p = cfg()
    return {k: p.get(k) for k in ("enabled", "daily_min", "start", "end", "warn_min")}


def usage_week():
    p = cfg()
    out = []
    for i in range(6, -1, -1):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        out.append({"day": d, "min": int(p.get("usage", {}).get(d, 0)) // 60})
    return out

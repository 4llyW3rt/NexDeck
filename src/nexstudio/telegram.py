"""
2.8.1: Ebeveyn kontrolü için Telegram köprüsü (sunucusuz; ebeveynin kendi botu).

Kurulum: ebeveyn @BotFather'dan bot açar, anahtarı Ebeveyn bölümüne yapıştırır; NexStudio 6 haneli bir eşleştirme kodu
gösterir, ebeveyn botuna "/start KOD" yazar -> o sohbet ebeveyn sohbeti olur. Başka sohbetlerden gelen her şey yok sayılır.

- Kilit ekranındaki "Ek süre iste" -> ebeveyne [+15] [+30] [+60] [Reddet] düğmeli mesaj; cevap bilgisayara anında işlenir.
- Komutlar: /durum, /ekle 30, /yardim
- Her gün 'report_time'da (varsayılan 21:00) günlük kullanım raporu.
Ağ: yalnızca https://api.telegram.org (ebeveynin bot anahtarıyla). Ayarlar: config.json > parental > telegram.
"""
import re
import secrets
import threading
import time
from datetime import datetime

from . import parental
from .core import CONFIG_LOCK, ui_log
from .i18n import ui_tr

API = "https://api.telegram.org/bot{token}/{method}"
REQUEST_COOLDOWN = 120   # sn: iki ek süre isteği arası
PENDING_TTL = 30 * 60    # sn: cevapsız istek bu kadar sonra düşer
PAIR_TTL = 10 * 60       # sn: eşleştirme kodu geçerlilik süresi
_session = None
_pair = {"code": "", "at": 0.0}   # eşleştirme kodu yalnızca bellekte

_thread = None
_stop = threading.Event()
_req = {"id": "", "state": "", "at": -10**9, "msg_id": 0}   # state: "" | pending | approved | denied
_lock = threading.RLock()


def tg_cfg():
    with CONFIG_LOCK:
        t = parental.cfg().setdefault("telegram", {})
        t.setdefault("token", ""); t.setdefault("chat_id", 0); t.setdefault("pair_code", "")
        t.setdefault("bot", ""); t.setdefault("report_time", "21:00"); t.setdefault("last_report", "")
        return t


def _sess():
    """Kullanıcı ortamındaki vekil sunucu / sertifika ayarlarına güvenilmez (araya girip onay taklidi olmasın)."""
    global _session
    if _session is None:
        import requests
        _session = requests.Session()
        _session.trust_env = False
        try:
            import certifi
            _session.verify = certifi.where()
        except ImportError:
            pass
    return _session


def _call(method, token=None, http_timeout=10, **params):
    import requests
    token = token or tg_cfg().get("token")
    if not token:
        raise ValueError("Telegram botu kurulu değil")
    try:
        r = _sess().post(API.format(token=token, method=method), json=params, timeout=http_timeout)
        data = r.json()
    except (requests.RequestException, ValueError):
        raise ValueError("Telegram sunucusuna ulaşılamadı")   # hata metninde anahtar görünmesin
    if not isinstance(data, dict) or not data.get("ok"):
        desc = data.get("description") if isinstance(data, dict) else ""
        raise ValueError(re.sub(r"bot[^/\s]+", "bot…", str(desc or "Telegram hatası")))
    return data.get("result")


def paired():
    t = tg_cfg()
    return bool(t.get("token") and t.get("chat_id"))


def send(text, **extra):
    t = tg_cfg()
    if not paired():
        return None
    return _call("sendMessage", chat_id=t["chat_id"], text=text, **extra)


# ----- kurulum (yalnızca yönetici oturumunda; app_api çağırır) -----
def set_token(token):
    parental.require_admin()
    if not isinstance(token, str) or not re.fullmatch(r"\d{3,15}:[A-Za-z0-9_-]{20,80}", token.strip()):
        raise ValueError("Bot anahtarı geçersiz")
    token = token.strip()
    me = _call("getMe", token=token)
    with CONFIG_LOCK:
        t = tg_cfg()
        t.update(token=token, bot=me.get("username", ""), chat_id=0, pair_code="")
        parental._save()
    _reset_request()
    _pair.update(code=f"{secrets.randbelow(10**6):06d}", at=time.monotonic())
    start()
    return {"bot": t["bot"], "pair_code": _pair["code"]}


def _reset_request():
    with _lock:
        _req.update(id="", state="", at=-10**9, msg_id=0)


def pair_code():
    if _pair["code"] and time.monotonic() - _pair["at"] > PAIR_TTL:
        _pair["code"] = ""   # süresi doldu
    return _pair["code"]


def disconnect():
    parental.require_admin()
    with CONFIG_LOCK:
        tg_cfg().update(token="", chat_id=0, pair_code="", bot="")
        parental._save()
    _reset_request()
    _pair["code"] = ""


def public():
    t = tg_cfg()
    if t.get("token") and not t.get("chat_id") and not pair_code():
        _pair.update(code=f"{secrets.randbelow(10**6):06d}", at=time.monotonic())   # süresi dolan kod yenilenir
    return {"bot": t.get("bot", ""), "paired": paired(), "pair_code": "" if t.get("chat_id") else pair_code(),
            "has_token": bool(t.get("token")), "report_time": t.get("report_time", "21:00")}


def set_report_time(value):
    parental.require_admin()
    v = str(value)
    if not (len(v) == 5 and v[2] == ":" and v[:2].isdigit() and v[3:].isdigit() and int(v[:2]) < 24 and int(v[3:]) < 60):
        raise ValueError("Saat SS:DD biçiminde olmalı")
    with CONFIG_LOCK:
        tg_cfg()["report_time"] = v
        parental._save()


# ----- ek süre isteği (kilit ekranından) -----
def request_state():
    with _lock:
        if _req["state"] == "pending" and time.monotonic() - _req["at"] > PENDING_TTL:
            _req["state"] = ""   # cevapsız istek düşer, yenisi gönderilebilir
        return dict(_req)


def clear_answered():
    """Kilit kalkınca eski 'reddedildi' bilgisi silinir."""
    with _lock:
        if _req["state"] in ("approved", "denied"):
            _req["state"] = ""


def request_extra():
    """Kilit ekranından: ebeveyne düğmeli mesaj gönderir."""
    if not paired():
        raise ValueError("Telegram bağlı değil")
    with _lock:
        if request_state()["state"] == "pending" or time.monotonic() - _req["at"] < REQUEST_COOLDOWN:
            raise ValueError("İstek zaten gönderildi; biraz bekle")
        rid = secrets.token_hex(4)
        st = parental.status()
        text = ui_tr("⏰ Ek süre isteniyor. Bugün {0} dk kullanıldı.", st["used_min"])
        kb = {"inline_keyboard": [[{"text": ui_tr("+{0} dk", m), "callback_data": f"x:{rid}:{m}"} for m in (15, 30, 60)],
                                  [{"text": ui_tr("Reddet"), "callback_data": f"n:{rid}:0"}]]}
        msg = send(text, reply_markup=kb)
        _req.update(id=rid, state="pending", at=time.monotonic(), msg_id=(msg or {}).get("message_id", 0))
    ui_log("👪 Telegram'dan ek süre istendi")


def _status_text():
    st = parental.status()
    left = "∞" if st["left_min"] is None else f"{st['left_min']} dk"
    state = ui_tr("Kilitli") if st["locked"] else (ui_tr("Etkin") if st["enabled"] else ui_tr("Kapalı"))
    left = "∞" if st["left_min"] is None else ui_tr("{0} dk", st["left_min"])
    return ui_tr("📊 Bugün: {0} dk kullanıldı, kalan {1}. Saatler {2}–{3}. Durum: {4}",
                 st["used_min"], left, st["start"], st["end"], state)


def _handle(update):
    t = tg_cfg()
    if "callback_query" in update:
        cq = update["callback_query"]
        chat = cq.get("message", {}).get("chat", {}).get("id")
        if not t.get("chat_id") or chat != t["chat_id"]:
            return
        kind, rid, minutes = ((cq.get("data") or "") + "::").split(":")[:3]
        ok_minutes = minutes.isdigit() and 1 <= int(minutes) <= 600
        with _lock:
            valid = rid and rid == _req["id"] and _req["state"] == "pending" and (kind == "n" or (kind == "x" and ok_minutes))
            if valid:
                _req["state"] = "approved" if kind == "x" else "denied"
        if valid and kind == "x":
            parental.grant_extra(int(minutes))
            ui_log(f"👪 Telegram'dan ek süre onaylandı: +{minutes} dk")
            answer = ui_tr("✅ +{0} dk verildi", minutes)
        elif valid:
            ui_log("👪 Telegram'dan ek süre reddedildi")
            answer = ui_tr("❌ Reddedildi")
        else:
            answer = ui_tr("Bu istek artık geçerli değil")
        try:
            _call("answerCallbackQuery", callback_query_id=cq["id"], text=answer)
            if valid:
                _call("editMessageText", chat_id=chat, message_id=cq["message"]["message_id"],
                      text=cq["message"].get("text", "") + "\n" + answer)
        except Exception:
            pass
        return
    msg = update.get("message") or {}
    chat = msg.get("chat", {}).get("id")
    text = (msg.get("text") or "").strip()
    if not chat or not text:
        return
    if not t.get("chat_id"):
        code = pair_code()
        first, _, rest = text.partition(" ")
        given = rest.strip() if first.lower().split("@")[0] == "/start" else text
        if code and given == code:
            with CONFIG_LOCK:
                t.update(chat_id=chat, pair_code="")
                parental._save()
            _pair["code"] = ""
            ui_log("👪 Telegram eşleşti")
            _call("sendMessage", chat_id=chat, text=ui_tr("✅ NexStudio bağlandı. Komutlar: /durum, /ekle 30, /yardim"))
        return
    if chat != t["chat_id"]:
        return
    cmd, _, arg = text.partition(" ")
    cmd = cmd.lower().split("@")[0]
    if cmd in ("/durum", "/status"):
        send(_status_text())
    elif cmd in ("/ekle", "/add"):
        try:
            mins = int(arg.strip())
            parental.grant_extra(mins)
            _reset_request()
            send(ui_tr("✅ +{0} dk verildi", mins) + "\n" + _status_text())
            ui_log(f"👪 Telegram'dan ek süre: +{mins} dk")
        except (ValueError, TypeError):
            send(ui_tr("Kullanım: /ekle 30 (1–600 dakika)"))
    else:
        send(ui_tr("Komutlar: /durum, /ekle 30"))


_report_lock = threading.Lock()


def _maybe_report():
    with _report_lock:   # iki yerden aynı anda çağrılırsa rapor iki kez gitmesin
        _maybe_report_locked()


def _maybe_report_locked():
    t = tg_cfg()
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    if not paired() or t.get("last_report") == today or now.strftime("%H:%M") < t.get("report_time", "21:00"):
        return
    send(ui_tr("🗓️ Günlük rapor") + "\n" + _status_text())   # önce gönder; başarısızsa sonra tekrar denenir
    with CONFIG_LOCK:
        t["last_report"] = today
        parental._save()


def _loop():
    offset, polled = 0, ""
    while not _stop.is_set():
        token = tg_cfg().get("token")
        if not token or (not parental.cfg().get("enabled") and paired()):
            _stop.wait(5)
            continue
        if token != polled:
            offset, polled = 0, token   # bot değişti: baştan oku
        try:
            updates = _call("getUpdates", token=token, http_timeout=35, offset=offset, timeout=25) or []
            if tg_cfg().get("token") != token:
                continue
            for u in updates:
                offset = max(offset, u["update_id"] + 1)
                try:
                    _handle(u)
                except Exception as e:
                    ui_log(f"⚠️ Telegram mesajı işlenemedi: {e}")
            _maybe_report()
        except Exception:
            _stop.wait(15)   # ağ yok / anahtar geçersiz: sessizce tekrar dene


def start():
    global _thread
    with _lock:
        _stop.clear()
        if _thread and _thread.is_alive():
            return
        _thread = threading.Thread(target=_loop, name="nexstudio-telegram", daemon=True)
        _thread.start()


def stop():
    _stop.set()

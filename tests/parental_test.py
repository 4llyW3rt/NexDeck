"""
2.8.0 ebeveyn kontrolü testi: kurulum, oturum, ayar doğrulama, kilit mantığı, kurtarma,
uzak erişim engeli, deneme modu günlükleri ve düz metin saklamama kontrolleri.
Çekirdeği NEXSTUDIO_PARENTAL_DRYRUN=1 ve QT_QPA_PLATFORM=offscreen ile ayrı veri klasöründe başlatır.
Kullanım:  python parental_test.py <src klasörü> <geçici veri klasörü>
"""
import ctypes
from ctypes import wintypes
import http.cookiejar
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta

SRC = os.path.abspath(sys.argv[1])
DATA = os.path.abspath(sys.argv[2])
os.makedirs(DATA, exist_ok=True)

results = []

SAFE_EXES = {
    "explorer.exe", "nexstudio.exe", "python.exe", "pythonw.exe", "dwm.exe", "csrss.exe", "winlogon.exe", "logonui.exe",
    "lockapp.exe", "shellexperiencehost.exe", "startmenuexperiencehost.exe", "searchhost.exe", "searchapp.exe",
    "textinputhost.exe", "ctfmon.exe", "sihost.exe", "fontdrvhost.exe", "msedgewebview2.exe", "applicationframehost.exe",
    "systemsettingsbroker.exe", "runtimebroker.exe", "dllhost.exe", "conhost.exe", "taskhostw.exe", "smartscreen.exe",
}


def has_non_safe_visible_window():
    """Mevcut masaüstünde SAFE_EXES dışında görünür ve başlıklı pencere var mı kontrol eder."""
    try:
        import psutil
        pids = set()
        user32 = ctypes.windll.user32
        proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def cb(hwnd, _):
            if user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd) > 0:
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                pids.add(pid.value)
            return True

        user32.EnumWindows(proc(cb), 0)
        for pid in pids:
            try:
                if psutil.Process(pid).name().lower() not in SAFE_EXES:
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def start_dummy_window_probe():
    """Boş/izole masaüstünde deneme modunu doğrulamak için zararsız görünür pencere (powershell.exe) açar."""
    ps_code = (
        'Add-Type -TypeDefinition \'using System; using System.Runtime.InteropServices; '
        'public class W { [DllImport("user32.dll", CharSet=CharSet.Unicode)] '
        'public static extern IntPtr CreateWindowExW(uint ex, string cls, string title, uint style, '
        'int x, int y, int w, int h, IntPtr parent, IntPtr menu, IntPtr inst, IntPtr param); }\'; '
        '$h = [W]::CreateWindowExW(0, "STATIC", "NexParentalDryRunProbe", 0x10000000, 0, 0, 10, 10, '
        '[IntPtr]::Zero, [IntPtr]::Zero, [IntPtr]::Zero, [IntPtr]::Zero); '
        'Start-Sleep -Seconds 30'
    )
    return subprocess.Popen(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_code],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=0x08000000,  # CREATE_NO_WINDOW
    )


def check(name, cond, detail=""):
    results.append((bool(cond), name))
    suffix = f" ({detail})" if detail and not cond else ""
    print(("PASS " if cond else "FAIL ") + name + suffix)


def is_port_45729_in_use():
    """Port 45729'a dokunmadan (bağlanmadan/bind etmeden) başka bir süreççe kullanılıp kullanılmadığını okur."""
    try:
        import psutil
        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr and conn.laddr.port == 45729 and conn.status == "LISTEN":
                return True
        return False
    except Exception:
        # Emin olunamıyorsa 45729'u kapma riskini alma (False -> web sunucusu testi atlanır)
        return False


def start_core(initial_config=None):
    if initial_config is not None:
        with open(os.path.join(DATA, "config.json"), "w", encoding="utf-8") as f:
            json.dump(initial_config, f, indent=2, ensure_ascii=False)
    for fname in ("runtime.json",):
        try:
            os.remove(os.path.join(DATA, fname))
        except FileNotFoundError:
            pass
    env = dict(
        os.environ,
        NEXSTUDIO_DATA_DIR=DATA,
        NEXSTUDIO_PARENTAL_DRYRUN="1",
        QT_QPA_PLATFORM="offscreen",
        PYTHONIOENCODING="utf-8",
    )
    proc = subprocess.Popen(
        [sys.executable, os.path.join(SRC, "nexstudio_ui.py")],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    rt_path = os.path.join(DATA, "runtime.json")
    for _ in range(50):
        if proc.poll() is not None:
            raise RuntimeError(f"Çekirdek erken kapandı (kod {proc.returncode})")
        if os.path.exists(rt_path):
            try:
                with open(rt_path, "r", encoding="utf-8") as f:
                    rt = json.load(f)
                if rt.get("port") and rt.get("token"):
                    return proc, rt
            except Exception:
                pass
        time.sleep(0.3)
    proc.kill()
    raise RuntimeError("runtime.json zamanında oluşmadı")


def stop_core(proc):
    if proc is None:
        return
    try:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=4)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=4)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def make_client(rt):
    def req_api(ep, body=None, raw_bytes=None):
        url = f"http://127.0.0.1:{rt['port']}/api2/{ep}"
        headers = {"X-Nex-Token": rt["token"], "Content-Type": "application/json"}
        if raw_bytes is not None:
            data = raw_bytes
        elif body is not None:
            data = json.dumps(body).encode("utf-8")
        else:
            data = None
        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            try:
                payload = json.loads(raw)
            except Exception:
                payload = {"raw": raw}
            return e.code, payload

    return req_api


core = None
dummy_win = None
try:
    # Temiz veri klasörü: önceki testten kalan yedek config'i de sil
    for fname in ("config.json", "config.json.bak", "runtime.json"):
        try:
            os.remove(os.path.join(DATA, fname))
        except FileNotFoundError:
            pass

    core, rt = start_core({"auto_connect": False, "welcome_done": True})
    api = make_client(rt)

    # ---- 1) Kurulum (setup) ----
    st, d = api("parental")
    check("başlangıçta setup=False ve dry_run=True", st == 200 and d.get("setup") is False and d.get("dry_run") is True, str(d))
    check("başlangıçta settings=None (oturum yok)", d.get("settings") is None and d.get("week") is None)

    st, d = api("parental", {"op": "setup", "password": "12345"})
    check("zayıf şifre (<6) reddedilir", st == 400 and d.get("ok") is False, f"{st} {d}")

    st, d = api("parental", {"op": "setup", "password": ""})
    check("boş şifre reddedilir", st == 400 and d.get("ok") is False, f"{st} {d}")

    PW1 = "EbeveynTest123!"
    st, d = api("parental", {"op": "setup", "password": PW1})
    code1 = d.get("recovery", "")
    check("ilk kurulum başarılı ve kurtarma kodu XXXX-XXXX-XXXX-XXXX biçiminde",
          st == 200 and d.get("ok") is True and bool(re.fullmatch(r"[0-9A-F]{4}(-[0-9A-F]{4}){3}", code1)),
          f"{st} {d}")

    st, d = api("parental", {"op": "setup", "password": "BaskaSifre99"})
    check("ikinci kurulum reddedilir", st == 400 and d.get("ok") is False, f"{st} {d}")

    # Kurulum sonrası otomatik yönetici oturumu açılır; çıkış yapıp settings=None doğrula
    st, d = api("parental")
    check("kurulum sonrası admin_left > 0 ve settings okunur",
          st == 200 and d.get("admin_left", 0) > 0 and isinstance(d.get("settings"), dict), str(d))

    st, d = api("parental", {"op": "logout"})
    check("logout başarılı", st == 200 and d.get("ok") is True)
    st, d = api("parental")
    check("oturumsuz settings=None ve admin_left=0",
          st == 200 and d.get("admin_left") == 0 and d.get("settings") is None and d.get("week") is None, str(d))

    # ---- 2) Düz metin saklamama (config.json) ----
    with open(os.path.join(DATA, "config.json"), "r", encoding="utf-8") as f:
        cfg_raw = f.read()
    cfg_json = json.loads(cfg_raw)
    pcfg = cfg_json.get("parental") or {}
    check("şifre config.json içinde düz metin değil ve salt$hash biçiminde",
          PW1 not in cfg_raw and "$" in str(pcfg.get("pw", "")) and len(str(pcfg.get("pw", ""))) > 40)
    check("kurtarma kodu config.json içinde düz metin değil ve salt$hash biçiminde",
          code1 not in cfg_raw and code1.replace("-", "") not in cfg_raw
          and "$" in str(pcfg.get("recovery", "")) and len(str(pcfg.get("recovery", ""))) > 40)

    # ---- 3) Yönetici oturumu (login / logout) ----
    st, d = api("parental", {"op": "login", "password": "YanlisSifre!"})
    check("yanlış şifreyle giriş -> 400", st == 400 and d.get("ok") is False, f"{st} {d}")

    st, d = api("parental", {"op": "login", "password": PW1})
    check("doğru şifreyle giriş -> 200", st == 200 and d.get("ok") is True, f"{st} {d}")

    st, d = api("parental")
    check("giriş sonrası admin_left > 0", st == 200 and d.get("admin_left", 0) > 0, str(d))

    st, d = api("parental", {"op": "logout"})
    check("çıkış -> 200", st == 200 and d.get("ok") is True)

    st, d = api("parental")
    check("çıkış sonrası admin_left == 0", st == 200 and d.get("admin_left") == 0, str(d))

    # ---- 4) Oturumsuz yönetici işlemlerinin reddedilmesi ----
    for op_name, payload in (
        ("settings", {"op": "settings", "values": {"enabled": True}}),
        ("password", {"op": "password", "password": "YeniSifre123"}),
        ("new_recovery", {"op": "new_recovery"}),
        ("extra", {"op": "extra", "minutes": 15}),
    ):
        st, d = api("parental", payload)
        check(f"oturumsuz op={op_name} reddedilir (400)", st == 400 and d.get("ok") is False, f"{st} {d}")

    # ---- 5) Ayar doğrulama (settings validation) ----
    api("parental", {"op": "login", "password": PW1})

    for bad_en in ("true", 1, None, []):
        st, d = api("parental", {"op": "settings", "values": {"enabled": bad_en}})
        check(f"non-bool enabled ({bad_en!r}) reddedilir", st == 400 and d.get("ok") is False, f"{st} {d}")

    for bad_time in ("25:00", "7:00", "ab:cd", "12:60", "24:00", "07:0"):
        st, d = api("parental", {"op": "settings", "values": {"start": bad_time}})
        check(f"geçersiz start saati ({bad_time!r}) reddedilir", st == 400 and d.get("ok") is False, f"{st} {d}")
        st, d = api("parental", {"op": "settings", "values": {"end": bad_time}})
        check(f"geçersiz end saati ({bad_time!r}) reddedilir", st == 400 and d.get("ok") is False, f"{st} {d}")

    # daily_min negative / huge clamped; warn_min low / high clamped
    st, d = api("parental", {"op": "settings", "values": {"daily_min": -50, "warn_min": 0}})
    cur = api("parental")[1]["settings"]
    check("daily_min negatif -> 0'a, warn_min 0 -> 1'e sıkıştırılır",
          st == 200 and cur["daily_min"] == 0 and cur["warn_min"] == 1, str(cur))

    st, d = api("parental", {"op": "settings", "values": {"daily_min": 99999, "warn_min": 999}})
    cur = api("parental")[1]["settings"]
    check("daily_min çok büyük -> 1440'a, warn_min çok büyük -> 30'a sıkıştırılır",
          st == 200 and cur["daily_min"] == 1440 and cur["warn_min"] == 30, str(cur))

    # ---- 6) Kilit mantığı: saat dışı ("hours"), yönetici muafiyeti, deneme modu logları ----
    now = datetime.now()
    excl_start = (now + timedelta(hours=2)).strftime("%H:%M")
    excl_end = (now + timedelta(hours=3)).strftime("%H:%M")
    st, d = api("parental", {"op": "settings", "values": {
        "enabled": True, "daily_min": 120, "start": excl_start, "end": excl_end, "warn_min": 5,
    }})
    check("saat dışı ayarları kaydedildi", st == 200 and d.get("ok") is True)

    st, d = api("parental")
    check("yönetici oturumundayken saat dışında bile locked=False",
          st == 200 and d.get("reason") == "hours" and d.get("locked") is False and d.get("admin_left", 0) > 0, str(d))

    # İzole/boş masaüstünde SAFE_EXES dışı pencere yoksa geçici zararsız bir test penceresi aç
    if not has_non_safe_visible_window():
        dummy_win = start_dummy_window_probe()
        for _ in range(30):
            if has_non_safe_visible_window():
                break
            time.sleep(0.2)

    # Log seq'ini al, sonra çıkış yap ki ParentalGuard.tick() kilide geçsin
    seq_before_lock = api("logs?since=0")[1].get("seq", 0)
    api("parental", {"op": "logout"})
    st, d = api("parental")
    check("oturum kapanınca saat dışında locked=True ve reason='hours'",
          st == 200 and d.get("locked") is True and d.get("reason") == "hours", str(d))

    # ParentalGuard.tick() 1 sn'de bir çalışır; kilidin ve dry-run enforce'un tetiklenmesini bekle
    time.sleep(2.2)
    logs_resp = api(f"logs?since={seq_before_lock}")[1]
    log_texts = [ln.get("text", "") for ln in logs_resp.get("lines", [])]
    has_kilit_log = any("Kilit: hours" in t for t in log_texts)
    has_dryrun_line = any("[deneme] kapatılırdı" in t for t in log_texts)
    has_real_kill = any("Kilitte kapatıldı" in t for t in log_texts)
    check("günlükte kilit olayı kaydedildi ('Kilit: hours')", has_kilit_log, str(log_texts))
    check("deneme modunda günlükte '[deneme] kapatılırdı' satırları göründü", has_dryrun_line, str(log_texts))
    check("deneme modunda gerçek kapatma YOK ('Kilitte kapatıldı' yok)", not has_real_kill, str(log_texts))
    if dummy_win is not None:
        check("deneme modunda test penceresi süreci gerçekten kapatılmadı (hayatta)", dummy_win.poll() is None)
        stop_core(dummy_win)
        dummy_win = None

    # Devre dışı (disabled) -> asla kilitlenmez
    api("parental", {"op": "login", "password": PW1})
    api("parental", {"op": "settings", "values": {"enabled": False}})
    api("parental", {"op": "logout"})
    st, d = api("parental")
    check("disabled (enabled=False) -> locked=False ve reason=''",
          st == 200 and d.get("locked") is False and d.get("reason") == "", str(d))

    # ---- 7) Kilit mantığı: günlük süre dolumu ("limit") + ek süre ("extra") ----
    # Çekirdeği durdur, config.json'a bugünkü kullanım >= 60 sn ve daily_min=1 yaz, yeniden başlat
    stop_core(core)
    core = None

    with open(os.path.join(DATA, "config.json"), "r", encoding="utf-8") as f:
        disk_cfg = json.load(f)
    now2 = datetime.now()
    incl_start = (now2 - timedelta(hours=2)).strftime("%H:%M")
    incl_end = (now2 + timedelta(hours=2)).strftime("%H:%M")
    today_str = now2.strftime("%Y-%m-%d")
    disk_cfg["parental"]["enabled"] = True
    disk_cfg["parental"]["daily_min"] = 1
    disk_cfg["parental"]["start"] = incl_start
    disk_cfg["parental"]["end"] = incl_end
    disk_cfg["parental"]["usage"] = {today_str: 65}
    disk_cfg["parental"]["extra"] = {}
    with open(os.path.join(DATA, "config.json"), "w", encoding="utf-8") as f:
        json.dump(disk_cfg, f, indent=2, ensure_ascii=False)
    # .bak da eski kalmasın
    try:
        os.remove(os.path.join(DATA, "config.json.bak"))
    except FileNotFoundError:
        pass

    core, rt = start_core(initial_config=None)
    api = make_client(rt)

    st, d = api("parental")
    check("daily_min=1 ve usage>=60s -> locked=True, reason='limit', left_min=0",
          st == 200 and d.get("locked") is True and d.get("reason") == "limit"
          and d.get("used_min", 0) >= 1 and d.get("left_min") == 0, str(d))

    # Yönetici oturumu ile ek süre ver ve çıkış yap -> left_min artar ve kilit açılır
    api("parental", {"op": "login", "password": PW1})
    st, d = api("parental", {"op": "extra", "minutes": 15})
    check("op=extra (+15 dk) başarılı", st == 200 and d.get("ok") is True, str(d))
    api("parental", {"op": "logout"})
    st, d = api("parental")
    check("ek süre sonrası left_min artar ve kilit açılır (locked=False)",
          st == 200 and d.get("locked") is False and d.get("extra_min") == 15 and (d.get("left_min") or 0) >= 14,
          str(d))

    # ---- 8) Kurtarma kodu (recovery) ----
    PW2 = "YeniEbeveyn456!"
    st, d = api("parental", {"op": "recover", "code": "0000-0000-0000-0000", "password": PW2})
    check("yanlış kurtarma kodu reddedilir", st == 400 and d.get("ok") is False, f"{st} {d}")

    st, d = api("parental", {"op": "recover", "code": code1, "password": PW2})
    code2 = d.get("recovery", "")
    check("doğru kurtarma kodu yeni şifre ve YENİ kurtarma kodu döner",
          st == 200 and d.get("ok") is True
          and bool(re.fullmatch(r"[0-9A-F]{4}(-[0-9A-F]{4}){3}", code2))
          and code2 != code1, f"{st} {d}")

    api("parental", {"op": "logout"})
    st, d = api("parental", {"op": "login", "password": PW1})
    check("eski şifre artık çalışmaz", st == 400 and d.get("ok") is False)

    st, d = api("parental", {"op": "login", "password": PW2})
    check("yeni şifre ile giriş başarılı", st == 200 and d.get("ok") is True)
    api("parental", {"op": "logout"})

    st, d = api("parental", {"op": "recover", "code": code1, "password": "BaskaSifre789!"})
    check("eski kurtarma kodu artık çalışmaz", st == 400 and d.get("ok") is False, f"{st} {d}")

    # Yeni şifre ve yeni kurtarma kodu da config.json'da düz metin değil
    with open(os.path.join(DATA, "config.json"), "r", encoding="utf-8") as f:
        cfg_raw2 = f.read()
    check("yeni şifre ve yeni kurtarma kodu da config.json'da düz metin değil",
          PW2 not in cfg_raw2 and code2 not in cfg_raw2 and code2.replace("-", "") not in cfg_raw2)

    # ---- 9) Uzak (telefon/web) erişim engeli -> 403 ----
    if is_port_45729_in_use():
        st, web = api("web", {"op": "start"})
        web_url = web.get("url", "")
        if ":45729/" in web_url:
            # Güvenlik ağı: asla 45729'u kullanma
            api("web", {"op": "stop"})
            print("SKIP uzak /api2/parental 403 kontrolü: web sunucusu port 45729'u alacaktı, durduruldu.")
        else:
            try:
                base = web_url.replace(web_url.split("/")[2].split(":")[0], "127.0.0.1")
                pin = web["pin"]
                jar = http.cookiejar.CookieJar()
                opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
                ua = "Mozilla/5.0 (Linux; Android 14; ParentalTestPhone) Chrome/120"
                # Önce geçerli oturum al (PIN ile)
                opener.open(urllib.request.Request(f"{base}?pin={pin}", headers={"User-Agent": ua}), timeout=15).read()

                def phone_call(method, ep, body=None):
                    h = {"User-Agent": ua, "Content-Type": "application/json"}
                    data = None if body is None else json.dumps(body).encode("utf-8")
                    r_req = urllib.request.Request(f"{base}/api2/{ep}", data=data, headers=h)
                    try:
                        with opener.open(r_req, timeout=15) as resp:
                            return resp.status, json.loads(resp.read().decode("utf-8"))
                    except urllib.error.HTTPError as e:
                        return e.code, json.loads((e.read() or b"{}").decode("utf-8", "replace"))

                gst, gd = phone_call("GET", "parental")
                check("telefondan GET /api2/parental -> 403 (local-only)", gst == 403 and gd.get("ok") is False, f"{gst} {gd}")
                pst, pd = phone_call("POST", "parental", {"op": "logout"})
                check("telefondan POST /api2/parental -> 403 (local-only)", pst == 403 and pd.get("ok") is False, f"{pst} {pd}")
            finally:
                api("web", {"op": "stop"})
    else:
        print("NOTE uzak web sunucusu başlatılmadı (port 45729 boşta/belirsiz -> gerçek uygulama portunu kapmamak için atlandı).")
        # Port açmadan AppApi.dispatch(..., remote=True) doğrulaması yap
        os.environ["NEXSTUDIO_DATA_DIR"] = DATA
        os.environ["NEXSTUDIO_PARENTAL_DRYRUN"] = "1"
        if SRC not in sys.path:
            sys.path.insert(0, SRC)
        from nexstudio.app_api import AppApi
        gst, gd = AppApi.dispatch("GET", "parental", {}, remote=True)
        pst, pd = AppApi.dispatch("POST", "parental", {"op": "logout"}, remote=True)
        check("AppApi.dispatch GET parental (remote=True) -> 403", gst == 403 and gd.get("ok") is False, f"{gst} {gd}")
        check("AppApi.dispatch POST parental (remote=True) -> 403", pst == 403 and pd.get("ok") is False, f"{pst} {pd}")

finally:
    stop_core(dummy_win)
    stop_core(core)

ok = all(r for r, _ in results)
print(f"\n{sum(r for r, _ in results)}/{len(results)} geçti")
sys.exit(0 if ok else 1)

"""
2.6.3 web erişim testi: PIN, oturum çerezi, bağlantıyı kesme, engelleme, onay, izin listesi.
Çekirdeği görünmez modda ayrı veri klasörüyle başlatır; her "telefon" ayrı çerez kavanozu + tarayıcı kimliğiyle davranır.
Kullanım:  python tests/web_access_test.py <src klasörü> <geçici veri klasörü>
"""
import hashlib, http.cookiejar, json, os, subprocess, sys, time, urllib.error, urllib.parse, urllib.request

SRC, DATA = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
os.makedirs(DATA, exist_ok=True)
# 2.7.1: eski sürümden kalan ayrı "TRUST-..." kaydı (IP + tarayıcı ile eşleşir) ve eşleşmeyen bir kayıt
LEGACY_UA, LEGACY_TOKEN = "Mozilla/5.0 (Linux; Android 13; LegacyPhone) Chrome/110 Mobile", "legacy-trust-token-271"
LEGACY_RAW = hashlib.sha256(f"127.0.0.1|{LEGACY_UA}".encode()).hexdigest()[:16]
json.dump({"ui_mode": "classic", "auto_connect": False, "welcome_done": True, "web_access_mode": "pin",
           "known_web_devices": {
               LEGACY_RAW: {"name": "Telefon - Chrome", "allowed": True, "user_agent": LEGACY_UA, "ip": "127.0.0.1",
                            "device_type": "Telefon", "browser": "Chrome", "last_seen": "2026-01-01 10:00:00"},
               "TRUST-aaaaaaaaaaaaaaaa": {"name": "Eski Telefonum", "allowed": True, "trusted": True,
                                          "trust_hash": hashlib.sha256(LEGACY_TOKEN.encode()).hexdigest(),
                                          "ip": "127.0.0.1", "user_agent": LEGACY_UA, "first_seen": "2026-01-01 09:00:00",
                                          "last_seen": "2026-01-01 10:00:00"},
               "TRUST-bbbbbbbbbbbbbbbb": {"name": "Eşleşmeyen", "allowed": True, "trusted": True, "trust_hash": "x" * 64,
                                          "last_seen": "2026-01-01 08:00:00"}}},
          open(os.path.join(DATA, "config.json"), "w", encoding="utf-8"))
for f in ("runtime.json",):
    try:
        os.remove(os.path.join(DATA, f))
    except FileNotFoundError:
        pass
env = dict(os.environ, NEXSTUDIO_DATA_DIR=DATA, QT_QPA_PLATFORM="offscreen", PYTHONIOENCODING="utf-8")
core = subprocess.Popen([sys.executable, os.path.join(SRC, "nexstudio_ui.py")], env=env,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
results = []


def check(name, cond):
    results.append((bool(cond), name))
    print(("PASS " if cond else "FAIL ") + name)


try:
    for _ in range(40):
        if os.path.exists(os.path.join(DATA, "runtime.json")):
            break
        time.sleep(0.5)
    rt = json.load(open(os.path.join(DATA, "runtime.json")))

    def local(ep, body=None):
        req = urllib.request.Request(f"http://127.0.0.1:{rt['port']}/api2/{ep}",
                                     data=None if body is None else json.dumps(body).encode(),
                                     headers={"X-Nex-Token": rt["token"], "Content-Type": "application/json"})
        return json.loads(urllib.request.urlopen(req, timeout=15).read())

    web = local("web", {"op": "start"})
    base = web["url"].replace(web["url"].split("/")[2].split(":")[0], "127.0.0.1")  # LAN ip yerine 127.0.0.1
    pin = web["pin"]

    class Phone:
        def __init__(self, ua):
            self.jar = http.cookiejar.CookieJar()
            self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
            self.ua = ua

        def get(self, path=""):
            req = urllib.request.Request(base + path, headers={"User-Agent": self.ua})
            try:
                r = self.op.open(req, timeout=15)
                return r.status, r.geturl(), r.read().decode("utf-8", "replace")
            except urllib.error.HTTPError as e:
                return e.code, base + path, e.read().decode("utf-8", "replace")

        def post(self, ep, body, pin_header=None):
            h = {"User-Agent": self.ua, "Content-Type": "application/json"}
            if pin_header:
                h["X-Nex-Pin"] = pin_header
            req = urllib.request.Request(f"{base}/api2/{ep}", data=json.dumps(body).encode(), headers=h)
            try:
                r = self.op.open(req, timeout=15)
                return r.status, json.loads(r.read())
            except urllib.error.HTTPError as e:
                return e.code, json.loads(e.read() or b"{}")

        def cookies(self):
            return {c.name for c in self.jar}

    profiles = local("state")["profiles"]

    # ---- 1) PIN modu
    a = Phone("Mozilla/5.0 (Linux; Android 14; TestPhone A) Chrome/120")
    st, url, body = a.get("")
    check("PIN'siz giriş sayfası açılır, uygulama açılmaz", st == 200 and "NEX_BOOT" not in body)
    st, url, body = a.get("?pin=ZZZZZZ")
    check("yanlış PIN reddedilir", "NEX_BOOT" not in body)
    check("yanlış PIN adres çubuğunda kalmaz, hata gösterilir", "pin=" not in url and "Hatalı PIN" in body)
    st, url, body = a.get(f"?pin={pin}")
    check("doğru PIN: uygulama açılır", st == 200 and "NEX_BOOT" in body)
    check("PIN adres çubuğundan temizlenir (yönlendirme)", "pin=" not in url)
    check("oturum çerezi verilir", "nexstudio_sess" in a.cookies())
    st, data = a.post("profile", {"op": "switch", "name": profiles[0]})
    check("oturum çereziyle (PIN'siz) yazma isteği çalışır", st == 200 and data.get("ok"))
    devs = local("web")["devices"]
    check("bağlanan cihaz listede ve 'şu an bağlı'", any(d["online"] for d in devs))
    dev_a = [d for d in devs if d["online"]][0]["id"]

    # ---- 2) Bağlantıyı kes
    local("known_device", {"op": "kick", "id": dev_a})
    st, data = a.post("profile", {"op": "switch", "name": profiles[0]})
    check("bağlantı kesilince eski oturum çalışmaz (401)", st == 401)
    st, url, body = a.get("")
    check("kesildikten sonra tekrar PIN istenir", "NEX_BOOT" not in body)

    # ---- 3) Engelle
    a.get(f"?pin={pin}")
    local("known_device", {"op": "block", "id": dev_a})
    st, url, body = a.get(f"?pin={pin}")
    check("engellenen cihaz doğru PIN'le de giremez (403)", st == 403 and "engellendi" in body)
    st, data = a.post("profile", {"op": "switch", "name": profiles[0]}, pin_header=pin)
    check("engellenen cihazın yazma isteği reddedilir", st in (401, 403))
    local("known_device", {"op": "unblock", "id": dev_a})
    st, url, body = a.get(f"?pin={pin}")
    check("engel kaldırılınca tekrar girebilir", "NEX_BOOT" in body)

    # ---- 4) Sadece onay modu
    local("settings", {"key": "web_access_mode", "value": "approve"})
    b = Phone("Mozilla/5.0 (iPad; CPU OS 17_0) Safari/605 TestTablet B")
    st, url, body = b.get("")
    check("onay modu: PIN sorulmadan bekleme sayfası", st == 200 and "Onay bekleniyor" in body)
    live = local("live?since=0")
    reqs = live.get("approvals", [])
    check("bilgisayarda onay isteği görünür", len(reqs) == 1)
    local("approval", {"id": reqs[0]["id"], "allow": True, "remember": True})
    st, url, body = b.get("")
    check("onaylanınca uygulama açılır", "NEX_BOOT" in body)
    check("'hatırla' seçilince kalıcı tanınma çerezi verilir", "nexstudio_trust" in b.cookies())
    c = Phone("Mozilla/5.0 (Windows NT 10.0) Firefox/120 TestPC C")
    c.get("")
    reqs = local("live?since=0").get("approvals", [])
    local("approval", {"id": reqs[0]["id"], "allow": False})
    st, url, body = c.get("")
    check("reddedilen cihaz giremez", st == 403 and "reddedildi" in body)

    # ---- 5) PIN + onay
    local("settings", {"key": "web_access_mode", "value": "pin_approve"})
    d = Phone("Mozilla/5.0 (Linux; Android 13) Chrome/119 TestPhone D")
    st, url, body = d.get("?pin=YYYYYY")
    check("PIN + onay: yanlış PIN'de bekleme sayfasına bile geçilmez", "Onay bekleniyor" not in body and "NEX_BOOT" not in body)
    st, url, body = d.get(f"?pin={pin}")
    check("PIN + onay: doğru PIN sonra onay beklenir", "Onay bekleniyor" in body)
    st, data = d.post("profile", {"op": "switch", "name": profiles[0]}, pin_header=pin)
    check("onaysız cihaz PIN'le API'ye yazamaz", st == 401)

    # ---- 6) Sadece izin verdiğim cihazlar
    local("settings", {"key": "web_access_mode", "value": "pin"})
    local("settings", {"key": "web_known_only", "value": True})
    e = Phone("Mozilla/5.0 (Linux; Android 12) Chrome/118 TestPhone E")
    st, url, body = e.get(f"?pin={pin}")
    check("izin listesi: yeni cihaz doğru PIN'le de giremez", st == 403)
    new = [x for x in local("web")["devices"] if not x["allowed"]]
    check("izinsiz deneme listede 'izinsiz' olarak görünür", len(new) >= 1)
    for x in new:
        local("known_device", {"op": "allow", "id": x["id"]})
    st, url, body = e.get(f"?pin={pin}")
    check("izin verilince girebilir", "NEX_BOOT" in body)
    check("telefondan yasak ayar reddedilir (run_in_bg)", e.post("settings", {"key": "run_in_bg", "value": True})[0] in (400, 403))
    # 2.7.3: telefon web modu tuş düzenini ve ekstra tekerlekleri değiştirebilir
    check("telefondan tuş düzeni değişir", e.post("settings", {"key": "web_layout", "value": "grid"})[0] == 200)
    check("telefondan ekstra tekerlek eklenir", e.post("settings", {"key": "extra_wheels", "value": [{"id": "t1", "target": "general_volume"}]})[0] == 200)
    check("telefondan geçersiz tekerlek hedefi reddedilir", e.post("settings", {"key": "extra_wheels", "value": [{"id": "t2", "target": "rm -rf"}]})[0] == 400)

    # ---- 7) 2.7.1: telefondan "Özel uygulama" atanamaz; atanmış tuşa basmak serbest
    lib = {}
    for grp in local("state")["library"]:
        for it in grp["items"]:
            lib.setdefault(it["needs"], (grp["cat"], it["name"]))
    app_cat, app_act = lib["app"]
    web_cat, web_act = lib["web"]
    plain_cat, plain_act = lib[""]
    st, data = e.post("assign", {"sig": "BTN:1", "cat": app_cat, "act": app_act, "arg": "C:/Windows/System32/calc.exe"})
    check("telefondan özel uygulama atanamaz", st in (400, 403) and "bilgisayardan" in data.get("error", ""))
    q = urllib.parse.urlencode({"sig": "BTN:1", "cat": app_cat, "act": app_act, "arg": "calc.exe"})
    st, _u, _b = e.get(f"/api/save?{q}")
    check("eski /api/save ucundan da özel uygulama atanamaz", st in (400, 403))
    check("özel uygulama tuşa yazılmadı", (local("state")["buttons"].get("BTN:1") or {}).get("needs") != "app")
    q = urllib.parse.urlencode({"sig": "../evil", "cat": plain_cat, "act": plain_act})
    check("eski /api/save geçersiz tuşu reddeder", e.get(f"/api/save?{q}")[0] == 400)
    q = urllib.parse.urlencode({"sig": "BTN:2", "cat": plain_cat, "act": plain_act})
    st, _u, body = e.get(f"/api/save?{q}")
    b2 = local("state")["buttons"].get("BTN:2") or {}
    check("eski /api/save geçerli atama yapar (emoji ile)", st == 200 and body == "OK" and b2.get("name") == plain_act and b2.get("emoji"))
    st, data = e.post("assign", {"sig": "BTN:3", "cat": web_cat, "act": web_act, "arg": 'x" & calc & "', "browser": "chrome"})
    check("telefondan tırnaklı web adresi reddedilir", st == 400)
    st, data = e.post("assign", {"sig": "BTN:3", "cat": web_cat, "act": web_act, "arg": "https://example.com/a?b=1&c=2"})
    check("telefondan normal web adresi atanır", st == 200 and data.get("ok"))
    r = local("assign", {"sig": "BTN:1", "cat": app_cat, "act": app_act, "arg": "nexstudio_qa_yok_271.exe", "app_action": "close"})
    check("bilgisayardan özel uygulama atanır", r.get("ok"))
    st, data = e.post("test", {"sig": "BTN:1"})
    check("telefondan atanmış özel uygulama tuşuna basılabilir", st == 200 and data.get("ok"))
    for sig in ("BTN:1", "BTN:2", "BTN:3"):
        local("clear", {"sig": sig})
    try:
        local("settings", {"key": "extra_wheels", "value": [{"id": "w1", "target": "rm -rf"}]})
        check("geçersiz ekstra tekerlek hedefi reddedilir", False)
    except urllib.error.HTTPError as ex:
        check("geçersiz ekstra tekerlek hedefi reddedilir", ex.code == 400 and "tekerlek" in json.loads(ex.read()).get("error", ""))

    # ---- 8) 2.7.1: "hatırla" ile onaylanan cihaz tek satır; kes / unut / engelle güveni kaldırır
    local("settings", {"key": "web_known_only", "value": False})
    local("settings", {"key": "web_access_mode", "value": "approve"})

    def approve_all(allow=True, remember=False):
        time.sleep(0.2)
        for r in local("live?since=0").get("approvals", []):
            local("approval", {"id": r["id"], "allow": allow, "remember": remember})

    f = Phone("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36")
    f.get("")
    approve_all(True, True)
    st, url, body = f.get("")
    check("hatırlanan cihaz girer", "NEX_BOOT" in body and "nexstudio_trust" in f.cookies())
    devs = local("web")["devices"]
    rows = [d for d in devs if "Pixel 8" in d["name"]]
    check("hatırlanan cihaz tek satır (TRUST- kopyası yok)", len(rows) == 1 and not rows[0]["id"].startswith("TRUST-"))
    check("varsayılan adda telefon modeli görünür", bool(rows) and rows[0]["name"].startswith("Pixel 8"))
    check("hatırlanan cihaz satırı 'şu an bağlı' ve tanınan", bool(rows) and rows[0]["online"] and rows[0]["trusted"])
    dev_f = rows[0]["id"]
    local("known_device", {"op": "kick", "id": dev_f})
    st, data = f.post("profile", {"op": "switch", "name": profiles[0]})
    check("hatırlanan cihaz kesilince yazamaz (401)", st == 401)
    st, url, body = f.get("")
    check("hatırlanan cihaz kesilince tekrar onay ister", "Onay bekleniyor" in body and "NEX_BOOT" not in body)
    approve_all(True, True)
    check("tekrar onaylanınca girer", "NEX_BOOT" in f.get("")[2])
    local("known_device", {"op": "forget", "id": dev_f})
    st, url, body = f.get("")
    check("unutulan hatırlanan cihaz tekrar onay ister", "Onay bekleniyor" in body)
    approve_all(True, True)
    check("unutulduktan sonra onayla girer", "NEX_BOOT" in f.get("")[2])
    local("known_device", {"op": "block", "id": dev_f})
    st, url, body = f.get("")
    check("hatırlanan cihaz engellenince giremez", st == 403 and "NEX_BOOT" not in body)
    local("known_device", {"op": "unblock", "id": dev_f})
    st, url, body = f.get("")
    check("engel kalkınca hatırlanma da kalkmış (onay ister)", "Onay bekleniyor" in body)
    approve_all(False)
    f.get("")

    # ---- 9) 2.7.1: "Sadece izin verdiğim cihazlar" + onay modu: bilgisayardan onay izin sayılır
    local("settings", {"key": "web_known_only", "value": True})
    g = Phone("Mozilla/5.0 (Linux; Android 14; SM-S911B) Chrome/120 Mobile TestPhone G")
    g.get("")
    approve_all(True, False)
    st, url, body = g.get("")
    check("izin listesi + onay: onaylanan yeni cihaz girer", st == 200 and "NEX_BOOT" in body)
    st, data = g.post("profile", {"op": "switch", "name": profiles[0]})
    check("izin listesi + onay: onaylanan cihaz API kullanır", st == 200 and data.get("ok"))
    local("settings", {"key": "web_known_only", "value": False})

    # ---- 10) 2.7.1: "Kodu yenile" sonrası eski adres: API 401 JSON, sayfa anlaşılır HTML
    old_base = base
    web = local("web", {"op": "reset"})
    base = web["url"].replace(web["url"].split("/")[2].split(":")[0], "127.0.0.1")

    def raw_open(url, data=None):
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            r = urllib.request.urlopen(req, timeout=15)
            return r.status, r.headers.get("Content-Type", ""), r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as ex:
            return ex.code, ex.headers.get("Content-Type", ""), ex.read().decode("utf-8", "replace")

    code, ctype, text = raw_open(f"{old_base}/api2/profile", b"{}")
    check("eski kodla POST 401 JSON", code == 401 and "json" in ctype and json.loads(text).get("ok") is False)
    code, ctype, text = raw_open(f"{old_base}/api2/live?since=0")
    check("eski kodla API GET 401 JSON", code == 401 and "json" in ctype and json.loads(text).get("ok") is False)
    code, ctype, text = raw_open(old_base)
    check("eski kodla sayfa: anlaşılır HTML", code == 403 and "text/html" in ctype and "Bağlantı kodu değişti" in text)

    # ---- 11) 2.7.1: eski "TRUST-" kaydı açılışta cihaz kaydıyla birleşir ve kaldırılabilir
    local("settings", {"key": "web_access_mode", "value": "pin"})
    ids = {d["id"]: d for d in local("web")["devices"]}
    check("eşleşen eski TRUST- kaydı birleşti", "TRUST-aaaaaaaaaaaaaaaa" not in ids and ids.get(LEGACY_RAW, {}).get("trusted"))
    check("eşleşmeyen eski TRUST- kaydı listede kalır", "TRUST-bbbbbbbbbbbbbbbb" in ids)

    def legacy_get():
        req = urllib.request.Request(base, headers={"User-Agent": LEGACY_UA, "Cookie": f"nexstudio_trust={LEGACY_TOKEN}"})
        try:
            return urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "replace")
        except urllib.error.HTTPError as ex:
            return ex.read().decode("utf-8", "replace")

    check("eski güven çereziyle PIN'siz girilir", "NEX_BOOT" in legacy_get())
    check("birleşen satırın adı korunur ve bağlı görünür",
          any(d["id"] == LEGACY_RAW and d["name"] == "Eski Telefonum" and d["online"] for d in local("web")["devices"]))
    local("known_device", {"op": "kick", "id": LEGACY_RAW})
    check("kesilince eski güven çereziyle girilemez", "NEX_BOOT" not in legacy_get())
    local("known_device", {"op": "forget", "id": "TRUST-bbbbbbbbbbbbbbbb"})
    check("eşleşmeyen eski kayıt unutulabilir", "TRUST-bbbbbbbbbbbbbbbb" not in {d["id"] for d in local("web")["devices"]})

    # ---- 12) 2.7.1: onay modunda giriş "Onaylı giriş" olarak kaydedilir
    time.sleep(0.5)
    hist = json.load(open(os.path.join(DATA, "config.json"), encoding="utf-8")).get("web_access_history", [])
    check("onay modundaki giriş 'Onaylı giriş' diye kaydedilir", any(h.get("detail") == "Onaylı giriş" for h in hist))
finally:
    core.kill()

ok = all(r for r, _ in results)
print(f"\n{sum(r for r, _ in results)}/{len(results)} geçti")
sys.exit(0 if ok else 1)

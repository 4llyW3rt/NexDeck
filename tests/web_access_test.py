"""
2.6.3 web erişim testi: PIN, oturum çerezi, bağlantıyı kesme, engelleme, onay, izin listesi.
Çekirdeği görünmez modda ayrı veri klasörüyle başlatır; her "telefon" ayrı çerez kavanozu + tarayıcı kimliğiyle davranır.
Kullanım:  python tests/web_access_test.py <src klasörü> <geçici veri klasörü>
"""
import http.cookiejar, json, os, subprocess, sys, time, urllib.error, urllib.request

SRC, DATA = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
os.makedirs(DATA, exist_ok=True)
json.dump({"ui_mode": "classic", "auto_connect": False, "welcome_done": True, "web_access_mode": "pin"},
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
    check("telefondan yasak işlem 403 (ayar değiştirme)", e.post("settings", {"key": "run_in_bg", "value": True})[0] == 403)
finally:
    core.kill()

ok = all(r for r, _ in results)
print(f"\n{sum(r for r, _ in results)}/{len(results)} geçti")
sys.exit(0 if ok else 1)

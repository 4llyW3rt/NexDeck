"""
2.7.1 API doğrulama testi: hatalı girdiler 500 yerine 400 döner, geçerli istekler hâlâ 200.
Çekirdeği görünmez modda ayrı veri klasörüyle başlatır. Bilgisayarda gerçek etkisi olan işlem yapmaz
(ses adımı hep 0, başlangıçta açılma açılmaz, tuş basılmaz, cihaza bağlanılmaz).
Kullanım:  python tests/api_validation_test.py <src klasörü> <geçici veri klasörü>
"""
import base64, io, json, os, subprocess, sys, time, urllib.error, urllib.request

SRC, DATA = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
os.makedirs(DATA, exist_ok=True)
for f in ("runtime.json", "config.json", "config.json.bak"):
    try:
        os.remove(os.path.join(DATA, f))
    except FileNotFoundError:
        pass
json.dump({"ui_mode": "classic", "auto_connect": False, "web_access_mode": "pin"},
          open(os.path.join(DATA, "config.json"), "w", encoding="utf-8"))
env = dict(os.environ, NEXSTUDIO_DATA_DIR=DATA, QT_QPA_PLATFORM="offscreen", PYTHONIOENCODING="utf-8")
core = subprocess.Popen([sys.executable, os.path.join(SRC, "nexstudio_ui.py")], env=env,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
results = []


def check(name, cond):
    results.append((bool(cond), name))
    print(("PASS " if cond else "FAIL ") + name)


def png_data_url():
    from PIL import Image
    out = io.BytesIO()
    Image.new("RGBA", (8, 8), (255, 0, 0, 255)).save(out, "PNG")
    return "data:image/png;base64," + base64.b64encode(out.getvalue()).decode("ascii")


try:
    for _ in range(60):
        if os.path.exists(os.path.join(DATA, "runtime.json")):
            break
        time.sleep(0.5)
    rt = json.load(open(os.path.join(DATA, "runtime.json")))
    BASE = f"http://127.0.0.1:{rt['port']}"

    def call(ep, body=None, raw=None, method=None):
        data = raw if raw is not None else (None if body is None else json.dumps(body).encode())
        req = urllib.request.Request(f"{BASE}/api2/{ep}", data=data, method=method,
                                     headers={"X-Nex-Token": rt["token"], "Content-Type": "application/json"})
        try:
            r = urllib.request.urlopen(req, timeout=15)
            return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def expect(name, ep, body, status, raw=None, err=None):
        st, res = call(ep, body, raw=raw)
        ok = st == status and (err is None or res.get("error") == err)
        check(f"{name} -> {status}" + ("" if ok else f" (gelen {st} {res.get('error')})"), ok)
        return res

    state = call("state")[1]
    lib = state["library"]
    cat, act = lib[0]["cat"], lib[0]["items"][0]["name"]
    auto_emoji = lib[0]["items"][0]["emoji"]

    # ---- 1) dispatch
    expect("JSON dizi gövde", "assign", None, 400, raw=b"[1,2]", err="Geçersiz istek")
    expect("JSON metin gövde", "assign", None, 400, raw=b'"x"', err="Geçersiz istek")
    expect("JSON sayı gövde", "theme", None, 400, raw=b"5", err="Geçersiz istek")

    # ---- 2) assign
    expect("assign cat liste", "assign", {"sig": "BTN:1", "cat": [1], "act": act}, 400)
    expect("assign act liste", "assign", {"sig": "BTN:1", "cat": cat, "act": ["a"]}, 400)
    expect("assign sig liste", "assign", {"sig": ["BTN:1"], "cat": cat, "act": act}, 400)
    for bad in ("BAD", "BTN:", "NEX:p3_b1", "WEB:P1", "ENC:UP", "BTN:1:SHORT", ""):
        expect(f"assign geçersiz sig {bad!r}", "assign", {"sig": bad, "cat": cat, "act": act}, 400)
    for good in ("BTN:1", "BTN:2:LONG", "ENC:BTN", "NEX:MIC_TOGGLE", "NEX:P3_B1", "WEB:P2_B5"):
        expect(f"assign geçerli sig {good}", "assign", {"sig": good, "cat": cat, "act": act}, 200)
    btn = call("state")[1]["buttons"].get("WEB:P2_B5", {})
    check("otomatik emoji kaydedildi", btn.get("emoji") == auto_emoji)
    expect("icon emoji seç", "icon", {"sig": "WEB:P2_B5", "emoji": "🦄"}, 200)
    expect("aynı görev yeniden atanır (ayar düzenleme)", "assign", {"sig": "WEB:P2_B5", "cat": cat, "act": act}, 200)
    check("kullanıcı emojisi korundu", call("state")[1]["buttons"]["WEB:P2_B5"]["emoji"] == "🦄")
    expect("aynı görev yeniden (otomatik emoji tuşu)", "assign", {"sig": "WEB:P2_B1", "cat": cat, "act": act}, 200)
    check("otomatik emoji otomatik kalır", call("state")[1]["buttons"]["WEB:P2_B1"]["emoji"] == auto_emoji)

    # ---- 7) icon / bg_image
    expect("icon data sayı", "icon", {"sig": "WEB:P2_B5", "data": 123}, 400, err="Geçersiz resim")
    expect("icon data virgülsüz", "icon", {"sig": "WEB:P2_B5", "data": "abc"}, 400, err="Geçersiz resim")
    expect("icon data resim değil", "icon", {"sig": "WEB:P2_B5", "data": "data:image/png;base64,AAAA"}, 400,
           err="Geçersiz resim")
    expect("icon data bozuk base64", "icon", {"sig": "WEB:P2_B5", "data": "data:image/png;base64,A"}, 400,
           err="Geçersiz resim")
    res = expect("icon geçerli PNG", "icon", {"sig": "WEB:P2_B5", "data": png_data_url()}, 200)
    check("ikon dosya adı döndü", str(res.get("icon", "")).startswith("icon_"))
    expect("bg_image resim değil", "bg_image", {"data": "data:image/jpeg;base64,AAAA"}, 400, err="Geçersiz resim")
    expect("bg_image temizle", "bg_image", {"data": ""}, 200)

    # ---- 5) page_name
    expect("page_name None", "page_name", {"page": "1", "name": None}, 400)
    expect("page_name nesne", "page_name", {"page": "1", "name": {"a": 1}}, 400)
    expect("page_name boş (varsayılana döner)", "page_name", {"page": "1", "name": ""}, 200)
    expect("page_name metin", "page_name", {"page": "w1", "name": "Oyun"}, 200)

    # ---- 6) encoder / volume
    expect("encoder bilinmeyen hedef", "encoder", {"turn": "bogus"}, 400)
    expect("encoder liste", "encoder", {"turn": ["general_volume"]}, 400)
    expect("encoder app_volume boş exe", "encoder", {"turn": "app_volume:"}, 400)
    expect("encoder app_volume", "encoder", {"turn": "app_volume:Discord.exe"}, 200)
    expect("encoder active_window", "encoder", {"turn": "active_window"}, 200)
    expect("encoder general_volume", "encoder", {"turn": "general_volume"}, 200)
    expect("volume steps null", "volume", {"steps": None}, 400)
    expect("volume steps liste", "volume", {"steps": [1]}, 400)
    expect("volume steps metin", "volume", {"steps": "abc"}, 400)
    expect("volume steps bool", "volume", {"steps": True}, 400)
    expect("volume bilinmeyen hedef", "volume", {"steps": 0, "target": "bogus"}, 400)
    expect("volume hedef liste", "volume", {"steps": 0, "target": ["x"]}, 400)
    expect("volume 0 adım geçerli hedef", "volume", {"steps": 0, "target": "brightness"}, 200)
    expect("volume 0 adım", "volume", {"steps": 0}, 200)

    # ---- 3) profiller
    default_profile = state["active_profile"]
    expect("profil adı nesne", "profile", {"op": "create", "name": {"a": 1}}, 400)
    expect("profil yeniden adlandır: olmayan", "profile", {"op": "rename", "name": "YOK", "new_name": "X"}, 400,
           err="Profil bulunamadı")
    expect("profil sil: olmayan", "profile", {"op": "delete", "name": "YOK"}, 400, err="Profil bulunamadı")
    expect("profil kopyala: olmayan kaynak", "profile", {"op": "copy", "name": "QA_K", "source": "YOK"}, 400,
           err="Profil bulunamadı")
    check("başarısız kopyada aktif profil değişmedi", call("state")[1]["active_profile"] == default_profile)
    expect("profil oluştur", "profile", {"op": "create", "name": "QA_A"}, 200)
    st = call("state")[1]
    check("yeni profil aktif ve boş (WEB:P2_B5 yok)", st["active_profile"] == "QA_A" and "WEB:P2_B5" not in st["buttons"])
    expect("profil kopyala (kaynak verilerek)", "profile", {"op": "copy", "name": "QA_B", "source": default_profile}, 200)
    st = call("state")[1]
    check("kopya kaynaktan alındı", st["active_profile"] == "QA_B" and "WEB:P2_B5" in st["buttons"])
    expect("profil kopyala (kaynaksız = aktif)", "profile", {"op": "copy", "name": "QA_C"}, 200)
    check("kaynaksız kopya aktif profilden", "WEB:P2_B5" in call("state")[1]["buttons"])
    expect("profil yeniden adlandır", "profile", {"op": "rename", "name": "QA_C", "new_name": "QA_D"}, 200)
    expect("profil sil", "profile", {"op": "delete", "name": "QA_D"}, 200)
    profs = call("state")[1]["profiles"]
    check("profil listesi doğru", "QA_D" not in profs and "QA_C" not in profs and "QA_B" in profs)
    expect("profil geçiş", "profile", {"op": "switch", "name": default_profile}, 200)

    # ---- 4) ayarlar
    for key in ("start_with_win", "run_in_bg", "auto_connect", "welcome_done", "dev_mode", "web_known_only", "update_check"):
        expect(f"{key} metin 'true'", "settings", {"key": key, "value": "true"}, 400)
        expect(f"{key} sayı 1", "settings", {"key": key, "value": 1}, 400)
    for key in ("run_in_bg", "dev_mode", "web_known_only", "start_with_win"):
        expect(f"{key} False", "settings", {"key": key, "value": False}, 200)
    expect("update_check False", "settings", {"key": "update_check", "value": False}, 200)
    check("state.settings.update_check False", call("state")[1]["settings"].get("update_check") is False)
    expect("update_check True", "settings", {"key": "update_check", "value": True}, 200)
    check("state.settings.update_check True", call("state")[1]["settings"].get("update_check") is True)
    expect("key_send_mode bilinmeyen", "settings", {"key": "key_send_mode", "value": "turbo"}, 400)
    expect("key_send_mode software", "settings", {"key": "key_send_mode", "value": "software"}, 200)
    expect("key_send_mode auto", "settings", {"key": "key_send_mode", "value": "auto"}, 200)
    expect("language liste", "settings", {"key": "language", "value": ["tr"]}, 400)
    expect("language sayı", "settings", {"key": "language", "value": 5}, 400)
    expect("language tr", "settings", {"key": "language", "value": "tr"}, 200)
    expect("extra_wheels metin", "settings", {"key": "extra_wheels", "value": "x"}, 400, err="Tekerlek listesi geçersiz")
    expect("extra_wheels null", "settings", {"key": "extra_wheels", "value": None}, 400, err="Tekerlek listesi geçersiz")
    expect("extra_wheels 7 adet", "settings", {"key": "extra_wheels", "value": [{}] * 7}, 400,
           err="En fazla 6 ekstra tekerlek eklenebilir")
    expect("extra_wheels None alanlar", "settings",
           {"key": "extra_wheels", "value": [{"id": None, "target": None}, {"id": 5, "target": ["x"]},
                                            {"id": "w1", "target": "app_volume:Discord.exe"}]}, 200)
    wheels = call("state")[1]["extra_wheels"]
    check("tekerlek id 'None' değil, hedef varsayılan",
          len(wheels) == 3 and all(w["id"] and w["id"] != "None" for w in wheels)
          and wheels[0]["target"] == "general_volume" and wheels[1]["target"] == "general_volume"
          and wheels[2] == {"id": "w1", "target": "app_volume:Discord.exe"})
    expect("extra_wheels geçersiz hedef", "settings", {"key": "extra_wheels", "value": [{"id": "w1", "target": "bogus"}]},
           400, err="Geçersiz tekerlek hedefi")   # 2.7.1
    expect("extra_wheels boş", "settings", {"key": "extra_wheels", "value": []}, 200)
    expect("web_grid liste", "settings", {"key": "web_grid", "value": [1, 2]}, 400)

    # ---- 8) welcome_done + app_mode art arda (arayüzün karşılama akışı)
    expect("welcome_done True", "settings", {"key": "welcome_done", "value": True}, 200)
    expect("app_mode web", "settings", {"key": "app_mode", "value": "web"}, 200)
    disk = json.load(open(os.path.join(DATA, "config.json"), encoding="utf-8-sig"))
    check("diskte welcome_done ve app_mode birlikte", disk.get("welcome_done") is True and disk.get("app_mode") == "web")
    call("web", {"op": "stop"})

    # ---- yerel çerez adı porta özel
    req = urllib.request.Request(f"{BASE}/app?t={rt['token']}")

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    try:
        urllib.request.build_opener(NoRedirect).open(req, timeout=10)
        set_cookie = ""
    except urllib.error.HTTPError as e:
        set_cookie = e.headers.get("Set-Cookie", "")
    check("çerez adı porta özel", set_cookie.startswith(f"nex_app_{rt['port']}="))

    def get_app(cookie):
        try:
            return urllib.request.urlopen(urllib.request.Request(f"{BASE}/app", headers={"Cookie": cookie}), timeout=10).status
        except urllib.error.HTTPError as e:
            return e.code
    check("porta özel çerezle giriş", get_app(f"nex_app_{rt['port']}={rt['token']}") == 200)
    check("eski ortak çerez adı geçersiz", get_app(f"nex_app={rt['token']}") == 403)

    # ---- hiçbiri error.log'a Traceback yazmamalı
    logs = call("logs?errors=1")[1].get("errors", "")
    check("error.log'da API hatası yok", "API hatası" not in logs)
finally:
    core.kill()

ok = all(r for r, _ in results)
print(f"\n{sum(r for r, _ in results)}/{len(results)} geçti")
sys.exit(0 if ok else 1)

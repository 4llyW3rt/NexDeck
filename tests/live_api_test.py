"""2.5 canlı olay testi: cihazdan gelen sinyaller /api2/live üzerinden arayüze ulaşıyor mu?
Kullanım: python tests/live_api_test.py <kaynak klasör> <geçici veri klasörü>
Görevler çalıştırılmaz (execute_macro devre dışı bırakılır)."""
import os, sys, json, time, urllib.request
os.environ["NEXSTUDIO_DATA_DIR"] = sys.argv[2]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, sys.argv[1])
from PyQt5.QtWidgets import QApplication
app = QApplication(sys.argv)
import nexstudio_ui as m
m.init_ui_bridge()
m.execute_macro = lambda action, droppable=True: None  # gerçek tuş basma yok
win = m.NexHubApp()

def get(ep):
    req = urllib.request.Request(f"http://127.0.0.1:{win.local_app.port}/api2/{ep}", headers={"X-Nex-Token": m.APP_API_TOKEN})
    return json.loads(urllib.request.urlopen(req, timeout=5).read())

results = []
first = get("live?since=-1")
results.append(("ilk çağrı olayları tekrar oynatmaz", first["events"] == []))
for sig in ["ENC:UP", "ENC:UP", "BTN:3", "NEX:MIC_TOGGLE"]:
    win.handle_serial_data(sig)
    time.sleep(0.16)  # çift sinyal korumasına takılmasın
r = get(f"live?since={first['seq']}")
results.append(("4 olay sırayla geldi", r["events"] == ["ENC:UP", "ENC:UP", "BTN:3", "NEX:MIC_TOGGLE"]))
r2 = get(f"live?since={r['seq']}")
results.append(("yeni olay yoksa boş liste", r2["events"] == []))
results.append(("bağlantı durumu alanı var", "connected" in r2))
for name, ok in results:
    print(("PASS " if ok else "FAIL ") + name)
win.force_quit()
sys.exit(0 if all(ok for _, ok in results) else 1)

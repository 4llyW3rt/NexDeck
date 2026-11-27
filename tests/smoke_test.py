"""NexStudio 2.0 duman testi: ayrı veri klasörüyle açar, temel akışları dener, ekran görüntüsü alır."""
import os, sys, time, json, shutil

SRC = os.path.abspath(sys.argv[1])
DATA = sys.argv[2]
OUT = sys.argv[3]
os.environ["NEXSTUDIO_DATA_DIR"] = DATA
sys.path.insert(0, SRC)
os.chdir(SRC)

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

app = QApplication(sys.argv)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _nex
m = _nex.load()  # 2.5.1: kod nexstudio paketinde; tüm modüller tek ad alanında
m.init_ui_bridge()
win = m.NexHubApp()
win.show()
results = []

def check(name, cond):
    results.append(("PASS" if cond else "FAIL", name))

def pump(sec):
    end = time.time() + sec
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)

pump(2.5)
for i in range(win.stack.count()):
    win.switch_main_page(i)
    pump(0.4)
    win.grab().save(os.path.join(OUT, f"page_{i}.png"))

# 1) Thread-güvenli log: arka thread'den log -> GUI'de görünmeli
import threading
threading.Thread(target=lambda: m.ui_log("TEST_FROM_THREAD")).start()
pump(0.5)
check("arka thread log GUI'ye ulaştı", "TEST_FROM_THREAD" in win.log_area.toPlainText())

# 2) Makro kuyruğu: GUI'yi bloklamamalı
calls = []
m.TASK_WORKER.submit(lambda: (time.sleep(0.8), calls.append(1)))
t0 = time.time(); app.processEvents(); dt = time.time() - t0
check("makro kuyruğu GUI'yi bloklamıyor", dt < 0.2)
pump(1.2)
check("kuyruktaki görev çalıştı", calls == [1])

# 3) Bayat görev atlanır
calls2 = []
m.TASK_WORKER.submit(lambda: time.sleep(2.0), droppable=False)
m.TASK_WORKER.submit(lambda: calls2.append("x"))
pump(2.6)
check("1.5 sn'den eski görev atlandı", calls2 == [])

# 4) Aynı sinyal 150ms içinde iki kez -> tek görev
executed = []
orig = m.execute_macro
m.execute_macro = lambda action, droppable=True: executed.append(action)
win.config.setdefault("buttons", {})["BTN:1"] = {"name": "t", "action": {"type": "native", "vk": 0x7C}}
win.handle_serial_data("BTN:1"); win.handle_serial_data("BTN:1")
check("çift sinyal tek görev", len(executed) == 1)
pump(0.2)
win.handle_serial_data("BTN:1")
check("150ms sonra tekrar çalışır", len(executed) == 2)
m.execute_macro = orig

# 5) Cihaz kimlik satırı
win.handle_serial_data("NEXDECK:READY;FW=2.0;CAP=HID,PING")
check("firmware yetenekleri okundu", win.device_supports_hid and win.device_supports_ping and win.device_fw == "2.0")

# 6) Profil değiştirme görevi
names = list(win.config["profiles"].keys())
before = win.config["active_profile"]
win.handle_profile_action({"type": "profile", "mode": "next"})
after = win.config["active_profile"]
check(f"sonraki profil ({before} -> {after})", len(names) < 2 or after != before)
win.handle_profile_action({"type": "profile", "mode": "switch", "custom_arg": before})
check("belirli profile dönüş", win.config["active_profile"] == before)

# 7) Atomik kayıt + bozuk dosyadan yedekle dönüş
m.save_config(win.config)
m.save_config(win.config)
cfg_path = m.CONFIG_FILE
check("config.json.bak oluştu", os.path.exists(cfg_path + ".bak"))
open(cfg_path, "w", encoding="utf-8").write("{bozuk")
data = m._read_config_file_safely()
check("bozuk config -> yedekten okundu", bool(data.get("profiles")))
m.save_config(win.config)

# 8) Bağlantı kopması akışı (sahte)
win._was_connected = True
win.on_serial_connection_error("test: kablo çıktı")
check("kopunca yeniden bağlanma zamanlayıcısı aktif", win.reconnect_timer.isActive() == bool(win.config.get("auto_connect", True)))
win.disconnect_device(user_requested=True)
check("kullanıcı kesince yeniden bağlanma durur", not win.reconnect_timer.isActive())

# 9) Profil kategorisi makrolarda
macros = m.get_all_macros()
check("Profil görev kategorisi var", "👤 Profil" in macros)
check("eklentiler yüklendi", len(m.LOADED_PLUGINS) > 0)

# 10) SendInput yapısı boyutu (64-bit: 40)
import ctypes
check("INPUT struct boyutu 40", ctypes.sizeof(m._INPUT) == 40)

check("nex API eklentiye enjekte", all(hasattr(v["module"], "nex") for v in m.LOADED_PLUGINS.values()))
check("paket eklentileri AppData'ya kopyalandı", os.path.exists(os.path.join(m.PLUGINS_DIR, "obs_studio.py")))
win.switch_main_page(0); pump(0.3)
win.grab().save(os.path.join(OUT, "home_after.png"))
with open(os.path.join(OUT, "results.txt"), "w", encoding="utf-8") as f:
    for r in results:
        f.write(f"{r[0]}  {r[1]}\n")
    f.write("\nLOG:\n" + win.log_area.toPlainText()[-3000:])
win.force_quit()

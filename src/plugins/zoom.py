# NexStudio 2.0: tuşlar nex.send_hotkey ile gönderilir (güvenilir SendInput / USB HID).
PLUGIN_NAME = "Zoom Kontrolleri"

ACTIONS = {
    "Mikrofonu Aç/Kapat (Alt+A)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "mic"},
    "Kamerayı Aç/Kapat (Alt+V)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "cam"},
    "Ekran Paylaşımı (Alt+S)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "share"},
    "Kaydı Başlat/Durdur (Alt+R)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "record"},
    "El Kaldır/İndir (Alt+Y)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "raise_hand"},
    "Toplantıdan Ayrıl (Alt+Q -> Enter)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "leave"}
}

def execute(func):
    import time
    if func == "mic": nex.send_hotkey("alt+a")
    elif func == "cam": nex.send_hotkey("alt+v")
    elif func == "share": nex.send_hotkey("alt+s")
    elif func == "record": nex.send_hotkey("alt+r")
    elif func == "raise_hand": nex.send_hotkey("alt+y")
    elif func == "leave":
        nex.send_hotkey("alt+q")
        time.sleep(0.5)
        nex.send_hotkey("enter")
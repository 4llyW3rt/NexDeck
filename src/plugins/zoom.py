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
    import keyboard, time
    if func == "mic": keyboard.send("alt+a")
    elif func == "cam": keyboard.send("alt+v")
    elif func == "share": keyboard.send("alt+s")
    elif func == "record": keyboard.send("alt+r")
    elif func == "raise_hand": keyboard.send("alt+y")
    elif func == "leave":
        keyboard.send("alt+q")
        time.sleep(0.5)
        keyboard.send("enter")
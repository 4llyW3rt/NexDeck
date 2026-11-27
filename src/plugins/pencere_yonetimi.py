# NexStudio 2.0: tuşlar nex.send_hotkey ile gönderilir (güvenilir SendInput / USB HID).
PLUGIN_NAME = "Pencere Yönetimi"

ACTIONS = {
    "Tam Ekran Yap (Win+Up)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "max"},
    "Aşağı İndir (Win+Down)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "min"},
    "Sola Yasla (Win+Left)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "left"},
    "Sağa Yasla (Win+Right)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "right"},
    "Diğer Ekrana Taşı (Win+Shift+Right)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "next_mon"},
    "Tüm Pencereleri Küçült (Win+D)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "desktop"}
}

def execute(func):
    if func == "max": nex.send_hotkey("windows+up")
    elif func == "min": nex.send_hotkey("windows+down")
    elif func == "left": nex.send_hotkey("windows+left")
    elif func == "right": nex.send_hotkey("windows+right")
    elif func == "next_mon": nex.send_hotkey("windows+shift+right")
    elif func == "desktop": nex.send_hotkey("windows+d")
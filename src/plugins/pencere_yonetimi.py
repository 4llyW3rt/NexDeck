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
    import keyboard
    if func == "max": keyboard.send("windows+up")
    elif func == "min": keyboard.send("windows+down")
    elif func == "left": keyboard.send("windows+left")
    elif func == "right": keyboard.send("windows+right")
    elif func == "next_mon": keyboard.send("windows+shift+right")
    elif func == "desktop": keyboard.send("windows+d")
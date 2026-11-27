# NexStudio 2.0: tuşlar nex.send_hotkey ile gönderilir (güvenilir SendInput / USB HID).
PLUGIN_NAME = "Adobe Photoshop"

ACTIONS = {
    "Yeni Dosya (Ctrl+N)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "new"},
    "Fırça Aracı (B)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "brush"},
    "Silgi Aracı (E)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "eraser"},
    "Geri Al (Ctrl+Z)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "undo"},
    "Web İçin Kaydet": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "save_web"}
}

def execute(func):
    if func == "new": nex.send_hotkey("ctrl+n")
    elif func == "brush": nex.send_hotkey("b")
    elif func == "eraser": nex.send_hotkey("e")
    elif func == "undo": nex.send_hotkey("ctrl+z")
    elif func == "save_web": nex.send_hotkey("ctrl+alt+shift+s")
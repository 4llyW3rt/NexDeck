PLUGIN_NAME = "Adobe Photoshop"

ACTIONS = {
    "Yeni Dosya (Ctrl+N)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "new"},
    "Fırça Aracı (B)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "brush"},
    "Silgi Aracı (E)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "eraser"},
    "Geri Al (Ctrl+Z)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "undo"},
    "Web İçin Kaydet": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "save_web"}
}

def execute(func):
    import keyboard
    if func == "new": keyboard.send("ctrl+n")
    elif func == "brush": keyboard.send("b")
    elif func == "eraser": keyboard.send("e")
    elif func == "undo": keyboard.send("ctrl+z")
    elif func == "save_web": keyboard.send("ctrl+alt+shift+s")
PLUGIN_NAME = "Adobe Premiere Pro"
ACTIONS = {
    "Kesme Aracı (Razor - C)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "razor"},
    "Seçim Aracı (V)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "select"},
    "Geri Al (Ctrl+Z)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "undo"},
    "Videoyu Dışa Aktar (Ctrl+M)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "export"}
}
def execute(func):
    import keyboard
    if func == "razor": keyboard.send("c")
    elif func == "select": keyboard.send("v")
    elif func == "undo": keyboard.send("ctrl+z")
    elif func == "export": keyboard.send("ctrl+m")
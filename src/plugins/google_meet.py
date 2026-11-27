PLUGIN_NAME = "Google Meet"
ACTIONS = {
    "Mikrofonu Aç/Kapat (Ctrl+D)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "mic"},
    "Kamerayı Aç/Kapat (Ctrl+E)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "cam"},
    "Sohbeti Aç/Kapat (Ctrl+Alt+C)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "chat"},
    "El Kaldır/İndir (Ctrl+Alt+H)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "hand"}
}
def execute(func):
    import keyboard
    if func == "mic": keyboard.send("ctrl+d")
    elif func == "cam": keyboard.send("ctrl+e")
    elif func == "chat": keyboard.send("ctrl+alt+c")
    elif func == "hand": keyboard.send("ctrl+alt+h")
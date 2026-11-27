# NexStudio 2.0: tuşlar nex.send_hotkey ile gönderilir (güvenilir SendInput / USB HID).
PLUGIN_NAME = "Google Meet"
ACTIONS = {
    "Mikrofonu Aç/Kapat (Ctrl+D)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "mic"},
    "Kamerayı Aç/Kapat (Ctrl+E)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "cam"},
    "Sohbeti Aç/Kapat (Ctrl+Alt+C)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "chat"},
    "El Kaldır/İndir (Ctrl+Alt+H)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "hand"}
}
def execute(func):
    if func == "mic": nex.send_hotkey("ctrl+d")
    elif func == "cam": nex.send_hotkey("ctrl+e")
    elif func == "chat": nex.send_hotkey("ctrl+alt+c")
    elif func == "hand": nex.send_hotkey("ctrl+alt+h")
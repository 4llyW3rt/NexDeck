# NexStudio 2.0: tuşlar nex.send_hotkey ile gönderilir (güvenilir SendInput / USB HID).
PLUGIN_NAME = "Adobe Premiere Pro"
ACTIONS = {
    "Kesme Aracı (Razor - C)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "razor"},
    "Seçim Aracı (V)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "select"},
    "Geri Al (Ctrl+Z)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "undo"},
    "Videoyu Dışa Aktar (Ctrl+M)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "export"}
}
def execute(func):
    if func == "razor": nex.send_hotkey("c")
    elif func == "select": nex.send_hotkey("v")
    elif func == "undo": nex.send_hotkey("ctrl+z")
    elif func == "export": nex.send_hotkey("ctrl+m")
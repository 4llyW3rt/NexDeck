# NexStudio 2.0: tuşlar nex.send_hotkey ile gönderilir (güvenilir SendInput / USB HID).
PLUGIN_NAME = "Microsoft Office (Word/Excel)"
ACTIONS = {
    "Kalın Yazı (Ctrl+B)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "bold"},
    "İtalik Yazı (Ctrl+I)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "italic"},
    "Kaydet (Ctrl+S)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "save"},
    "Kopyala (Ctrl+C)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "copy"},
    "Yapıştır (Ctrl+V)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "paste"}
}
def execute(func):
    if func == "bold": nex.send_hotkey("ctrl+b")
    elif func == "italic": nex.send_hotkey("ctrl+i")
    elif func == "save": nex.send_hotkey("ctrl+s")
    elif func == "copy": nex.send_hotkey("ctrl+c")
    elif func == "paste": nex.send_hotkey("ctrl+v")
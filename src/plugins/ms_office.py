PLUGIN_NAME = "Microsoft Office (Word/Excel)"
ACTIONS = {
    "Kalın Yazı (Ctrl+B)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "bold"},
    "İtalik Yazı (Ctrl+I)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "italic"},
    "Kaydet (Ctrl+S)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "save"},
    "Kopyala (Ctrl+C)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "copy"},
    "Yapıştır (Ctrl+V)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "paste"}
}
def execute(func):
    import keyboard
    if func == "bold": keyboard.send("ctrl+b")
    elif func == "italic": keyboard.send("ctrl+i")
    elif func == "save": keyboard.send("ctrl+s")
    elif func == "copy": keyboard.send("ctrl+c")
    elif func == "paste": keyboard.send("ctrl+v")
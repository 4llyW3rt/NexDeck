PLUGIN_NAME = "VS Code Araçları"

ACTIONS = {
    "Komut Paleti (Ctrl+Shift+P)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "cmd_palette"},
    "Terminali Aç/Kapat (Ctrl+`)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "terminal"},
    "Dosyayı Kaydet (Ctrl+S)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "save"},
    "Dosya Aç (Ctrl+O)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "open"},
    "Kodu Formatla (Shift+Alt+F)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "format"},
    "Satırı Yorum Yap (Ctrl+K, Ctrl+C)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "comment"}
}

def execute(func):
    import keyboard, time
    if func == "cmd_palette": keyboard.send("ctrl+shift+p")
    elif func == "terminal": keyboard.send("ctrl+`")
    elif func == "save": keyboard.send("ctrl+s")
    elif func == "open": keyboard.send("ctrl+o")
    elif func == "format": keyboard.send("shift+alt+f")
    elif func == "comment":
        keyboard.send("ctrl+k")
        time.sleep(0.2)
        keyboard.send("ctrl+c")
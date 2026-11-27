# NexStudio 2.0: tuşlar nex.send_hotkey ile gönderilir (güvenilir SendInput / USB HID).
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
    import time
    if func == "cmd_palette": nex.send_hotkey("ctrl+shift+p")
    elif func == "terminal": nex.send_hotkey("ctrl+`")
    elif func == "save": nex.send_hotkey("ctrl+s")
    elif func == "open": nex.send_hotkey("ctrl+o")
    elif func == "format": nex.send_hotkey("shift+alt+f")
    elif func == "comment":
        nex.send_hotkey("ctrl+k")
        time.sleep(0.2)
        nex.send_hotkey("ctrl+c")
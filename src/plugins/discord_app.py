# NexStudio 2.0: tuşlar nex.send_hotkey ile gönderilir (güvenilir SendInput / USB HID).
PLUGIN_NAME = "Discord Kontrolleri"

ACTIONS = {
    "Sustur / Aç (Mute)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "mute"},
    "Sağırlaş / Aç (Deafen)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "deafen"},
    "Aramayı Yanıtla": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "answer"},
    "Aramayı Reddet / Kapat": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "decline"},
    "Discord'u Öne Getir": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "focus"}
}

def execute(func):
    import ctypes, subprocess
    if func == "mute": nex.send_hotkey("ctrl+shift+m")
    elif func == "deafen": nex.send_hotkey("ctrl+shift+d")
    elif func == "answer": nex.send_hotkey("ctrl+enter")
    elif func == "decline": nex.send_hotkey("esc")
    elif func == "focus":
        try:
            output = subprocess.check_output('tasklist /FI "IMAGENAME eq Discord.exe" /NH /FO CSV', shell=True).decode('utf-8', errors='ignore')
            pids = [int(line.split('","')[1].strip('"')) for line in output.split('\n') if 'Discord.exe' in line]
            if not pids: return
            def foreach_window(hwnd, lParam):
                pid = ctypes.c_ulong()
                ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value in pids and ctypes.windll.user32.IsWindowVisible(hwnd):
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                    return False
                return True
            ctypes.windll.user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))(foreach_window), 0)
        except: pass
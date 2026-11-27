PLUGIN_NAME = "Spotify Kontrolleri"

ACTIONS = {
    "Oynat/Duraklat": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "pp"},
    "Sonraki Şarkı": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "next"},
    "Önceki Şarkı": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "prev"},
    "Karışık Çal (Shuffle)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "shuffle"},
    "Tekrarla (Repeat)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "repeat"}
}

def execute(func):
    import ctypes, subprocess
    try:
        output = subprocess.check_output('tasklist /FI "IMAGENAME eq spotify.exe" /NH /FO CSV', shell=True).decode('utf-8', errors='ignore')
        spotify_pids = [int(line.split('","')[1].strip('"')) for line in output.split('\n') if 'spotify.exe' in line.lower()]
    except: return
    if not spotify_pids: return

    def foreach_window(hwnd, lParam):
        pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in spotify_pids and ctypes.windll.user32.GetWindowTextLengthW(hwnd) > 0:
            if func == "pp": ctypes.windll.user32.SendMessageW(hwnd, 0x0319, 0, 14 << 16)
            elif func == "next": ctypes.windll.user32.SendMessageW(hwnd, 0x0319, 0, 11 << 16)
            elif func == "prev": ctypes.windll.user32.SendMessageW(hwnd, 0x0319, 0, 12 << 16)
            elif func == "shuffle":
                import keyboard
                ctypes.windll.user32.SetForegroundWindow(hwnd)
                keyboard.send("ctrl+s")
            elif func == "repeat":
                import keyboard
                ctypes.windll.user32.SetForegroundWindow(hwnd)
                keyboard.send("ctrl+r")
            return False
        return True
    ctypes.windll.user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))(foreach_window), 0)
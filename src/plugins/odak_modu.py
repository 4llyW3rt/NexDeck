PLUGIN_NAME = "Odak Modu (Focus)"

ACTIONS = {
    "Odak Modunu Başlat": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "start_focus"},
    "Odak Modunu Bitir": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "stop_focus"}
}

def execute(func):
    import subprocess, ctypes, time
    
    if func == "start_focus":
        # 1. Discord'u sağırlaştır (Deafen) - Rahatsız edilmemek için
        import keyboard
        keyboard.send("ctrl+shift+d")
        
        # 2. Windows Odaklanma Yardımcısını (Focus Assist) aç
        subprocess.Popen("ms-settings:quiethours", shell=True)
        time.sleep(1)
        keyboard.send("tab")
        keyboard.send("space")
        keyboard.send("alt+f4") # Ayarları kapat
        
        print("Odak Modu BAŞLADI: Discord sağırlaştırıldı, bildirimler kapatıldı.")
        
    elif func == "stop_focus":
        # 1. Discord sağırlaştırmayı kapat
        import keyboard
        keyboard.send("ctrl+shift+d")
        
        print("Odak Modu BİTTİ: Normale dönüldü.")
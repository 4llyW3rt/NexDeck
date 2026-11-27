# NexStudio 2.0: tuşlar nex.send_hotkey ile gönderilir (güvenilir SendInput / USB HID).
PLUGIN_NAME = "Odak Modu (Focus)"

ACTIONS = {
    "Odak Modunu Başlat": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "start_focus"},
    "Odak Modunu Bitir": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "stop_focus"}
}

def execute(func):
    import subprocess, ctypes, time
    
    if func == "start_focus":
        # 1. Discord'u sağırlaştır (Deafen) - Rahatsız edilmemek için
        nex.send_hotkey("ctrl+shift+d")
        
        # 2. Windows Odaklanma Yardımcısını (Focus Assist) aç
        subprocess.Popen("ms-settings:quiethours", shell=True)
        time.sleep(1)
        nex.send_hotkey("tab")
        nex.send_hotkey("space")
        nex.send_hotkey("alt+f4") # Ayarları kapat
        
        print("Odak Modu BAŞLADI: Discord sağırlaştırıldı, bildirimler kapatıldı.")
        
    elif func == "stop_focus":
        # 1. Discord sağırlaştırmayı kapat
        nex.send_hotkey("ctrl+shift+d")
        
        print("Odak Modu BİTTİ: Normale dönüldü.")
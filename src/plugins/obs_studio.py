PLUGIN_NAME = "OBS Studio (API)"

ACTIONS = {
    "Yayını Başlat/Durdur": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "toggle_stream"},
    "Kaydı Başlat/Durdur": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "toggle_record"},
    "Kaydı Duraklat": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "pause_record"},
    "Kaydı Devam Ettir": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "resume_record"},
    "Tekrar Oynatmayı (Replay Buffer) Kaydet": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "save_replay"},
    "Stüdyo Modunu Aç/Kapat": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "toggle_studio_mode"},
    "Mikrofonu Sustur/Aç": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "toggle_mic"},
    "Masaüstü Sesini Sustur/Aç": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "toggle_desktop"},
    "Sahne 1'e Geç": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "scene_1"},
    "Sahne 2'ye Geç": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "scene_2"},
    "Sahne 3'e Geç": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "scene_3"},
    "Sahne 4'e Geç": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "scene_4"},
    "Sahne 5'e Geç": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "scene_5"}
}

def execute(func):
    try:
        import obsws_python as obs
        client = obs.ReqClient(host='localhost', port=4455, password='')
        
        if func == "toggle_stream": client.toggle_stream()
        elif func == "toggle_record": client.toggle_record()
        elif func == "pause_record": client.pause_record()
        elif func == "resume_record": client.resume_record()
        elif func == "save_replay": client.save_replay_buffer()
        elif func == "toggle_studio_mode": client.set_studio_mode_enabled(not client.get_studio_mode_enabled().studio_mode_enabled)
        elif func == "toggle_mic": client.toggle_input_mute("Mic/Aux")
        elif func == "toggle_desktop": client.toggle_input_mute("Desktop Audio")
        elif func == "scene_1": client.set_current_program_scene("Sahne 1")
        elif func == "scene_2": client.set_current_program_scene("Sahne 2")
        elif func == "scene_3": client.set_current_program_scene("Sahne 3")
        elif func == "scene_4": client.set_current_program_scene("Sahne 4")
        elif func == "scene_5": client.set_current_program_scene("Sahne 5")
    except Exception as e:
        print("OBS Bağlantı Hatası:", e)
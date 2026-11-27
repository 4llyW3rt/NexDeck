# NexStudio 2.0: OBS WebSocket eklentisi
# - Bağlantı her basışta yeniden kurulmaz; açık bağlantı tekrar kullanılır (daha hızlı, donma yok).
# - Bağlantı ayarları ve sahne adları config.json > plugin_settings > "OBS Studio (API)" altından okunur:
#     "host": "localhost", "port": 4455, "password": "", "scenes": ["Sahne 1", "Sahne 2", ...],
#     "mic_source": "Mic/Aux", "desktop_source": "Desktop Audio"
# - Hatalar sessizce yutulmaz, Sistem Günlüğü'ne yazılır.
import threading

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
    "Sahne 5'e Geç": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "scene_5"},
}

_client = None
_lock = threading.Lock()


def _setting(key, default):
    try:
        return nex.get_setting(key, default)  # noqa: F821 (NexStudio tarafından eklenir)
    except Exception:
        return default


def _log(msg):
    try:
        nex.log(msg)  # noqa: F821
    except Exception:
        print(msg)


def _get_client(force_new=False):
    global _client
    import obsws_python as obs
    if _client is None or force_new:
        _client = obs.ReqClient(
            host=_setting("host", "localhost"),
            port=int(_setting("port", 4455)),
            password=_setting("password", ""),
            timeout=3,
        )
    return _client


def _scene_name(index):
    scenes = _setting("scenes", None)
    if isinstance(scenes, list) and len(scenes) >= index:
        return scenes[index - 1]
    return f"Sahne {index}"


def _run(func, client):
    if func == "toggle_stream": client.toggle_stream()
    elif func == "toggle_record": client.toggle_record()
    elif func == "pause_record": client.pause_record()
    elif func == "resume_record": client.resume_record()
    elif func == "save_replay": client.save_replay_buffer()
    elif func == "toggle_studio_mode":
        client.set_studio_mode_enabled(not client.get_studio_mode_enabled().studio_mode_enabled)
    elif func == "toggle_mic": client.toggle_input_mute(_setting("mic_source", "Mic/Aux"))
    elif func == "toggle_desktop": client.toggle_input_mute(_setting("desktop_source", "Desktop Audio"))
    elif func.startswith("scene_"):
        client.set_current_program_scene(_scene_name(int(func.split("_")[1])))


def execute(func):
    try:
        import obsws_python  # noqa: F401
    except ImportError:
        _log("obsws-python kütüphanesi bulunamadı. (pip install obsws-python)")
        return
    with _lock:
        try:
            _run(func, _get_client())
        except Exception as first_error:
            # Bağlantı kopmuş olabilir (OBS yeniden açıldı vb.): bir kez yeniden bağlanıp dene.
            try:
                _run(func, _get_client(force_new=True))
            except Exception as e:
                global _client
                _client = None
                _log(f"OBS'e bağlanılamadı veya komut başarısız: {e or first_error}. "
                     "OBS > Araçlar > WebSocket Sunucu Ayarları'nın açık olduğunu kontrol edin.")

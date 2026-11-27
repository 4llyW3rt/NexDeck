# NexStudio — NEXSTUDIO ÖZGÜR YAZILIM LİSANSI (NPL-v2), Telif Hakkı (c) 2026 Ali Mert Taşcı / NexHub. Ayrıntılar: LICENSE.txt

"""Görev motoru: tuş/sinyal tanımları, hazır görevler, eklentiler, profiller, ayar dosyası, execute_macro."""
from . import state
from .core import (  # noqa: F401
    CONFIG_BACKUP_FILE,
    CONFIG_FILE,
    CONFIG_LOCK,
    HAS_KEYBOARD,
    NIRCMD_PATH,
    PLUGINS_DIR,
    TASK_WORKER,
    WEB_HISTORY_LIMIT,
    copy,
    datetime,
    get_resource_path,
    glob,
    importlib,
    json,
    keyboard,
    os,
    run_on_ui,
    secrets,
    send_key_combo,
    shutil,
    socket,
    subprocess,
    threading,
    time,
    traceback,
    ui_log,
    webbrowser,
    write_error_log,
)
from .i18n import (  # noqa: F401
    tr,
)

# =========================================================
# 4. WINDOWS API VE NATIVE MAKROLAR
# =========================================================
VK_MEDIA_NEXT_TRACK, VK_MEDIA_PREV_TRACK, VK_MEDIA_PLAY_PAUSE, VK_VOLUME_MUTE = 0xB0, 0xB1, 0xB3, 0xAD
VK_VOLUME_UP, VK_VOLUME_DOWN = 0xAF, 0xAE
VK_F13, VK_F14, VK_F15, VK_F16 = 0x7C, 0x7D, 0x7E, 0x7F
VK_F17, VK_F18, VK_F19, VK_F20 = 0x80, 0x81, 0x82, 0x83
VK_F21, VK_F22, VK_F23, VK_F24 = 0x84, 0x85, 0x86, 0x87

VK_MAP = {
    'ctrl': 0x11, 'shift': 0x10, 'alt': 0x12, 'win': 0x5B, 'enter': 0x0D, 'space': 0x20, 'tab': 0x09, 'esc': 0x1B, 'backspace': 0x08,
    'print screen': 0x2C, 'printscreen': 0x2C, 'prtsc': 0x2C,
    'up': 0x26, 'down': 0x28, 'left': 0x25, 'right': 0x27,
    'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45, 'f': 0x46, 'g': 0x47, 'h': 0x48, 'i': 0x49, 'j': 0x4A, 'k': 0x4B, 'l': 0x4C, 'm': 0x4D, 'n': 0x4E, 'o': 0x4F, 'p': 0x50, 'q': 0x51, 'r': 0x52, 's': 0x53, 't': 0x54, 'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58, 'y': 0x59, 'z': 0x5A,
    '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34, '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
    'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73, 'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77, 'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
    'f13': 0x7C, 'f14': 0x7D, 'f15': 0x7E, 'f16': 0x7F, 'f17': 0x80, 'f18': 0x81, 'f19': 0x82, 'f20': 0x83, 'f21': 0x84, 'f22': 0x85, 'f23': 0x86, 'f24': 0x87,
    'control': 0x11, 'windows': 0x5B, 'escape': 0x1B, 'return': 0x0D,
    'delete': 0x2E, 'del': 0x2E, 'insert': 0x2D, 'ins': 0x2D, 'home': 0x24, 'end': 0x23,
    'pageup': 0x21, 'page up': 0x21, 'pgup': 0x21, 'pagedown': 0x22, 'page down': 0x22, 'pgdn': 0x22,
    '`': 0xC0
}

# Windows VK -> USB HID usage kodu. Cihaz "USB klavye" modunda bu kodları gerçek klavye gibi basar.
# Firmware: kod >= 0xE0 ise modifier (Ctrl/Shift/Alt/Win), değilse normal tuş.
HID_KEY_CODES = {
    0x11: 0xE0, 0x10: 0xE1, 0x12: 0xE2, 0x5B: 0xE3,
    0x0D: 0x28, 0x1B: 0x29, 0x08: 0x2A, 0x09: 0x2B, 0x20: 0x2C, 0x2C: 0x46,
    0x2D: 0x49, 0x24: 0x4A, 0x21: 0x4B, 0x2E: 0x4C, 0x23: 0x4D, 0x22: 0x4E,
    0x27: 0x4F, 0x25: 0x50, 0x28: 0x51, 0x26: 0x52,
    0x6F: 0x54, 0x6A: 0x55, 0x6D: 0x56, 0x6B: 0x57, 0x60: 0x62, 0x6E: 0x63,
    0xC0: 0x35,
}
HID_KEY_CODES.update({0x41 + i: 0x04 + i for i in range(26)})              # A-Z
HID_KEY_CODES.update({0x31 + i: 0x1E + i for i in range(9)})               # 1-9
HID_KEY_CODES[0x30] = 0x27                                                  # 0
HID_KEY_CODES.update({0x70 + i: 0x3A + i for i in range(12)})              # F1-F12
HID_KEY_CODES.update({0x7C + i: 0x68 + i for i in range(12)})              # F13-F24
HID_KEY_CODES.update({0x61 + i: 0x59 + i for i in range(9)})               # Numpad 1-9

def press_key(vk_code):
    send_key_combo([vk_code])

def get_physical_buttons():
    return {
        "BTN:1": tr("btn_1"), "BTN:2": tr("btn_2"), "BTN:3": tr("btn_3"), "BTN:4": tr("btn_4"), "BTN:5": tr("btn_5"), 
        "BTN:1:LONG": tr("btn_1_l"), "BTN:2:LONG": tr("btn_2_l"), "BTN:3:LONG": tr("btn_3_l"), "BTN:4:LONG": tr("btn_4_l"), "BTN:5:LONG": tr("btn_5_l"), 
        "ENC:BTN": tr("enc_btn")
    }

# Nextion ekrandan GELEN GERÇEK sinyaller.
# Bundan sonra dokunmatik görevleri bu sinyal adlarına göre kaydedilir ve çalıştırılır.
# Fiziksel tuşlar/encoder bu yapıdan bağımsızdır.
TOUCH_PAGE_SIGNALS = {
    1: [
        "NEX:MIC_TOGGLE",
        "NEX:DESK_TOGGLE",
        "NEX:CAM_TOGGLE",
        "NEX:LIVE_TOGGLE",
        "NEX:SCENE_1",
        "NEX:SCENE_2",
        "NEX:SCENE_3",
    ],
    2: [
        "NEX:MEDIA_PREV",
        "NEX:MEDIA_PP",
        "NEX:MEDIA_NEXT",
        "NEX:REC_TOGGLE",
        "NEX:OPEN_YT",
        "NEX:OPEN_KICK",
    ],
    3: [
        "NEX:P3_B1",
        "NEX:P3_B2",
        "NEX:P3_B3",
        "NEX:P3_B4",
        "NEX:P3_B5",
        "NEX:P3_B6",
    ],
    4: [
        "NEX:P4_B1",
        "NEX:P4_B2",
        "NEX:P4_B3",
        "NEX:P4_B4",
        "NEX:P4_B5",
        "NEX:P4_B6",
    ],
}

# UI'da 8 slot var; bazı slotlar ileri/geri sayfa tuşu ve görev almaz.
# Bu eşleşme sadece uygulamadaki görsel slotu gerçek Nextion görev sinyaline bağlar.
TOUCH_UI_SLOT_TO_SIGNAL = {
    1: {
        0: "NEX:MIC_TOGGLE",
        1: "NEX:DESK_TOGGLE",
        2: "NEX:CAM_TOGGLE",
        3: "NEX:LIVE_TOGGLE",
        4: "NEX:SCENE_1",
        5: "NEX:SCENE_2",
        6: "NEX:SCENE_3",
    },
    2: {
        0: "NEX:MEDIA_PREV",
        1: "NEX:MEDIA_PP",
        2: "NEX:MEDIA_NEXT",
        3: "NEX:REC_TOGGLE",
        # slot 4 geri tuşudur
        5: "NEX:OPEN_YT",
        6: "NEX:OPEN_KICK",
        # slot 7 ileri tuşudur
    },
    3: {
        0: "NEX:P3_B1",
        1: "NEX:P3_B2",
        2: "NEX:P3_B3",
        3: "NEX:P3_B4",
        # slot 4 geri tuşudur
        5: "NEX:P3_B5",
        6: "NEX:P3_B6",
        # slot 7 ileri tuşudur
    },
    4: {
        0: "NEX:P4_B1",
        1: "NEX:P4_B2",
        2: "NEX:P4_B3",
        3: "NEX:P4_B4",
        # slot 4 geri tuşudur
        5: "NEX:P4_B5",
        6: "NEX:P4_B6",
        # slot 7 ileri tuşudur / son sayfada pasif
    },
}

# Sayfa 3-4'te ekrana yazı göndermek için UI slotundan gerçek Nextion obje adına gideriz.
# Bu sadece ekran yazısı güncelleme içindir; görev çalıştırma için sinyal çevrilmez.
NEXTION_TEXT_OBJ_BY_SLOT = {
    # Sadece Nextion ekranındaki yazıları güncellemek için kullanılır.
    # Görev çalıştırma tarafı cihazdan gelen gerçek sinyalleri kullanır.
    3: {
        0: "b0",
        1: "b1",
        2: "b2",
        3: "b3",
        5: "b4",  # P3_B5
        6: "b5",  # P3_B6; b6 ileri tuşu olduğu için buraya yazılmamalı
    },
    4: {
        0: "b1",
        1: "b2",
        2: "b3",
        3: "b4",
        5: "b5",
        6: "b7",  # P4_B6 yazısı buraya gitmeli; b6 ileri tuşuna yazıyordu
    },
}

# Reset sırasında daha önce yanlışlıkla yazı gitmiş olabilecek tüm b0-b7 objelerini temizliyoruz.
NEXTION_TEXT_RESET_OBJS = {
    3: ["b0", "b1", "b2", "b3", "b4", "b5", "b6", "b7"],
    4: ["b0", "b1", "b2", "b3", "b4", "b5", "b6", "b7"],
}

def is_valid_user_task(cfg):
    return bool(isinstance(cfg, dict) and cfg.get("action"))

def should_ignore_serial_signal(data):
    if not isinstance(data, str):
        return False
    data = data.strip()
    return (
        not data
        or data.startswith("DEBUG_NEX_SENT:")
        or data.startswith("NEXCMD:")
        or data.startswith("page")
    )

def resolve_nextion_signal(data, buttons_cfg):
    """
    Dokunmatik ekran sinyalinde çeviri yapmaz.
    Nextion hangi sinyali gönderiyorsa görev o anahtarda aranır.
    (2.0: önceki sürümlerden kalan erişilemeyen eski eşleme kodu kaldırıldı.)
    """
    if not isinstance(data, str):
        return data
    return data.strip()

def get_builtin_macros():
    return {
        tr("cat_custom"): {
            tr("act_custom_web"): {"type": "custom_web"},
            tr("act_custom_app"): {"type": "custom_app"},
            tr("act_custom_hotkey"): {"type": "custom_hotkey"}
        },
        tr("cat_text"): {
            tr("act_text_type"): {"type": "type_text"}
        },
        tr("cat_fkeys"): {
            "F13": {"type": "native", "vk": VK_F13}, "F14": {"type": "native", "vk": VK_F14},
            "F15": {"type": "native", "vk": VK_F15}, "F16": {"type": "native", "vk": VK_F16},
            "F17": {"type": "native", "vk": VK_F17}, "F18": {"type": "native", "vk": VK_F18},
            "F19": {"type": "native", "vk": VK_F19}, "F20": {"type": "native", "vk": VK_F20},
            "F21": {"type": "native", "vk": VK_F21}, "F22": {"type": "native", "vk": VK_F22},
            "F23": {"type": "native", "vk": VK_F23}, "F24": {"type": "native", "vk": VK_F24}
        },
        tr("cat_numpad"): {
            "Numpad 0": {"type": "native", "vk": 0x60}, "Numpad 1": {"type": "native", "vk": 0x61},
            "Numpad 2": {"type": "native", "vk": 0x62}, "Numpad 3": {"type": "native", "vk": 0x63},
            "Numpad 4": {"type": "native", "vk": 0x64}, "Numpad 5": {"type": "native", "vk": 0x65},
            "Numpad 6": {"type": "native", "vk": 0x66}, "Numpad 7": {"type": "native", "vk": 0x67},
            "Numpad 8": {"type": "native", "vk": 0x68}, "Numpad 9": {"type": "native", "vk": 0x69},
            "Numpad *": {"type": "native", "vk": 0x6A}, "Numpad +": {"type": "native", "vk": 0x6B},
            "Numpad -": {"type": "native", "vk": 0x6D}, "Numpad .": {"type": "native", "vk": 0x6E},
            "Numpad /": {"type": "native", "vk": 0x6F}
        },
        tr("cat_win"): {
            tr("act_win_max"): {"type": "custom_hotkey", "custom_arg": "win+up"},
            tr("act_win_min"): {"type": "custom_hotkey", "custom_arg": "win+down"},
            tr("act_win_left"): {"type": "custom_hotkey", "custom_arg": "win+left"},
            tr("act_win_right"): {"type": "custom_hotkey", "custom_arg": "win+right"},
            tr("act_win_next"): {"type": "custom_hotkey", "custom_arg": "win+shift+right"},
            tr("act_win_d"): {"type": "custom_hotkey", "custom_arg": "win+d"}
        },
        tr("cat_snip"): {
            tr("act_snip_reg"): {"type": "cmd", "cmd": "start ms-screenclip:"},
            tr("act_snip_full"): {"type": "custom_hotkey", "custom_arg": "win+print screen"},
            tr("act_snip_app"): {"type": "cmd", "cmd": "snippingtool.exe"}
        },
        tr("cat_power"): {
            tr("act_pow_sleep"): {"type": "cmd", "cmd": "rundll32.exe powrprof.dll,SetSuspendState 0,1,0"},
            tr("act_pow_shut"): {"type": "cmd", "cmd": "shutdown /s /t 0"},
            tr("act_pow_res"): {"type": "cmd", "cmd": "shutdown /r /t 0"},
            tr("act_pow_lock"): {"type": "cmd", "cmd": "rundll32.exe user32.dll,LockWorkStation"}
        },
        tr("cat_media"): {
            tr("act_media_pp"): {"type": "native", "vk": VK_MEDIA_PLAY_PAUSE},
            tr("act_media_next"): {"type": "native", "vk": VK_MEDIA_NEXT_TRACK},
            tr("act_media_prev"): {"type": "native", "vk": VK_MEDIA_PREV_TRACK},
            tr("act_media_mute"): {"type": "native", "vk": VK_VOLUME_MUTE}
        },
        tr("cat_vol"): {
            tr("act_vol_up"): {"type": "native", "vk": VK_VOLUME_UP},
            tr("act_vol_down"): {"type": "native", "vk": VK_VOLUME_DOWN},
            tr("act_vol_foc_up"): {"type": "nircmd", "cmd": "changeappvolume focused 0.01"},
            tr("act_vol_foc_down"): {"type": "nircmd", "cmd": "changeappvolume focused -0.01"}
        },
        tr("cat_web"): {
            tr("act_web_yt"): {"type": "web", "cmd": "https://www.youtube.com/@NexHubCo/@NexHubCo"},
            tr("act_web_kick"): {"type": "web", "cmd": "https://kick.com"}
        },
        "👤 Profil": dict(
            [
                ("Sonraki Profile Geç", {"type": "profile", "mode": "next"}),
                ("Önceki Profile Geç", {"type": "profile", "mode": "prev"}),
            ]
            + [
                (f"'{name}' profiline geç", {"type": "profile", "mode": "switch", "custom_arg": name})
                for name in (state.APP_CONFIG.get("profiles") or {}).keys()
            ]
        ),
        tr("cat_tools"): {
            tr("act_tool_exp"): {"type": "cmd", "cmd": "explorer.exe"},
            tr("act_tool_calc"): {"type": "cmd", "cmd": "calc.exe"},
            tr("act_tool_task"): {"type": "cmd", "cmd": "taskmgr.exe"}
        }
    }

FACTORY_DEFAULT_BUTTONS = {
    # Sayfa 1 - cihazdan gelen gerçek klasik sinyaller
    "NEX:MIC_TOGGLE": {"name": "F13", "action": {"type": "native", "vk": VK_F13}},
    "NEX:DESK_TOGGLE": {"name": "F14", "action": {"type": "native", "vk": VK_F14}},
    "NEX:CAM_TOGGLE": {"name": "F15", "action": {"type": "native", "vk": VK_F15}},
    "NEX:LIVE_TOGGLE": {"name": "F16", "action": {"type": "native", "vk": VK_F16}},
    "NEX:SCENE_1": {"name": "F17", "action": {"type": "native", "vk": VK_F17}},
    "NEX:SCENE_2": {"name": "F18", "action": {"type": "native", "vk": VK_F18}},
    "NEX:SCENE_3": {"name": "F19", "action": {"type": "native", "vk": VK_F19}},

    # Sayfa 2 - cihazdan gelen gerçek klasik sinyaller
    "NEX:MEDIA_PREV": {"name": "Önceki Şarkı", "action": {"type": "native", "vk": VK_MEDIA_PREV_TRACK}},
    "NEX:MEDIA_PP": {"name": "Oynat/Duraklat", "action": {"type": "native", "vk": VK_MEDIA_PLAY_PAUSE}},
    "NEX:MEDIA_NEXT": {"name": "Sonraki Şarkı", "action": {"type": "native", "vk": VK_MEDIA_NEXT_TRACK}},
    "NEX:REC_TOGGLE": {"name": "F20", "action": {"type": "native", "vk": VK_F20}},
    "NEX:OPEN_YT": {"name": "YouTube", "action": {"type": "web", "cmd": "https://www.youtube.com/@NexHubCo"}},
    "NEX:OPEN_KICK": {"name": "Kick", "action": {"type": "web", "cmd": "https://kick.com"}},
}

class NexPluginAPI:
    """
    Eklentilere verilen yardımcı API (eklentide `nex` adıyla erişilir).
      nex.send_hotkey("ctrl+shift+m")   -> NexStudio'nun güvenilir tuş gönderimi (SendInput / USB HID)
      nex.log("mesaj")                  -> Sistem günlüğüne yazar
      nex.get_setting("anahtar", varsayılan) / nex.set_setting("anahtar", değer)
                                         -> config.json > plugin_settings > <eklenti adı>
    """

    def __init__(self, plugin_name):
        self.plugin_name = plugin_name

    def send_hotkey(self, combo):
        keys = [k.strip().lower() for k in str(combo).split("+") if k.strip()]
        vk_list = [VK_MAP[k] for k in keys if k in VK_MAP]
        if len(vk_list) != len(keys):
            raise ValueError(f"Tanınmayan tuş: {combo}")
        if not _send_hotkey_via_device(vk_list):
            send_key_combo(vk_list)

    def log(self, message):
        ui_log(f"🧩 {self.plugin_name}: {message}")

    def get_setting(self, key, default=None):
        return (state.APP_CONFIG.get("plugin_settings", {}).get(self.plugin_name, {})).get(key, default)

    def set_setting(self, key, value):
        with CONFIG_LOCK:
            state.APP_CONFIG.setdefault("plugin_settings", {}).setdefault(self.plugin_name, {})[key] = value
        save_config(state.APP_CONFIG)


def seed_bundled_plugins():
    """
    Kurulumla gelen eklentileri kullanıcının eklenti klasörüne kopyalar.
    (1.x'te paketlenen eklentiler AppData'ya hiç kopyalanmıyordu.)
    Paketteki dosya daha yeniyse eski dosya .bak olarak saklanıp güncellenir.
    """
    bundled_dir = get_resource_path("plugins")
    if not os.path.isdir(bundled_dir) or os.path.abspath(bundled_dir) == os.path.abspath(PLUGINS_DIR):
        return
    for src in glob.glob(os.path.join(bundled_dir, "*.py")):
        dst = os.path.join(PLUGINS_DIR, os.path.basename(src))
        try:
            if not os.path.exists(dst):
                shutil.copy2(src, dst)
            elif os.path.getmtime(src) > os.path.getmtime(dst) + 1:
                with open(src, "rb") as a, open(dst, "rb") as b:
                    if a.read() == b.read():
                        continue
                shutil.copy2(dst, dst + ".bak")
                shutil.copy2(src, dst)
                ui_log(f"🧩 Eklenti güncellendi: {os.path.basename(src)} (eski hali .bak olarak saklandı)")
        except Exception as e:
            write_error_log(f"Eklenti kopyalanamadı ({src}): {e}")


state.LOADED_PLUGINS = {}
def load_plugins():
    state.LOADED_PLUGINS = {}
    state.PLUGIN_LANGUAGES = {}
    seed_bundled_plugins()
    for file_path in glob.glob(os.path.join(PLUGINS_DIR, "*.py")):
        module_name = os.path.basename(file_path)[:-3]
        try:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            module.nex = NexPluginAPI(module_name)  # modül çalışmadan önce erişilebilir olsun
            spec.loader.exec_module(module)
            if hasattr(module, "PLUGIN_NAME"):
                module.nex.plugin_name = module.PLUGIN_NAME
            # 2.6: eklenti dil paketi ekleyebilir: LANGUAGES = {"de": {"name": ..., "ui": {...}, "core": {...}}}
            if isinstance(getattr(module, "LANGUAGES", None), dict):
                state.PLUGIN_LANGUAGES.update(module.LANGUAGES)
                if not hasattr(module, "ACTIONS"):
                    continue
            if hasattr(module, "PLUGIN_NAME") and hasattr(module, "ACTIONS"):
                state.LOADED_PLUGINS[module.PLUGIN_NAME] = {"actions": module.ACTIONS, "module": module, "file": file_path}
            else:
                ui_log(f"⚠️ Eklenti atlandı ({os.path.basename(file_path)}): PLUGIN_NAME veya ACTIONS tanımlı değil.")
        except Exception as e:
            write_error_log(f"Eklenti yüklenemedi ({file_path}):\n" + traceback.format_exc())
            ui_log(f"⚠️ Eklenti yüklenemedi ({os.path.basename(file_path)}): {e}")

def get_all_macros():
    all_macros = get_builtin_macros()
    for plugin_name, plugin_data in state.LOADED_PLUGINS.items():
        all_macros[f"🧩 {plugin_name}"] = plugin_data["actions"]
    return all_macros

PROFILE_KEYS = ["buttons", "encoder", "page_names", "screen_bg"]
DEFAULT_PROFILE_NAME = "Varsayılan"
DEFAULT_MOBILE_PORT = 45729
MOBILE_PORT_RANGE = 20

def find_available_port(start_port=DEFAULT_MOBILE_PORT, count=MOBILE_PORT_RANGE):
    """45729'dan başlayarak gerçekten boş port bulur."""
    for port in range(start_port, start_port + count):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                # SO_REUSEADDR kullanılmaz: Windows'ta dolu portu da "boş" gösteriyordu.
                if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                sock.bind(("0.0.0.0", port))
                return port
        except OSError:
            continue
    return None


def snapshot_profile_data(config_data):
    return {
        "buttons": copy.deepcopy(config_data.get("buttons", FACTORY_DEFAULT_BUTTONS.copy())),
        "encoder": copy.deepcopy(config_data.get("encoder", {"turn": "general_volume"})),
        "page_names": copy.deepcopy(config_data.get("page_names", {})),
        "screen_bg": config_data.get("screen_bg", "")
    }

def ensure_profiles(config_data, update_active=False):
    if "profiles" not in config_data or not isinstance(config_data.get("profiles"), dict):
        config_data["profiles"] = {}

    active = config_data.get("active_profile") or DEFAULT_PROFILE_NAME
    config_data["active_profile"] = active

    if not config_data["profiles"]:
        config_data["profiles"][active] = snapshot_profile_data(config_data)

    if active not in config_data["profiles"]:
        config_data["profiles"][active] = snapshot_profile_data(config_data)

    if update_active:
        config_data["profiles"][active] = snapshot_profile_data(config_data)

    return config_data

def apply_active_profile(config_data):
    ensure_profiles(config_data, update_active=False)
    active = config_data.get("active_profile", DEFAULT_PROFILE_NAME)
    pdata = config_data.get("profiles", {}).get(active, {})
    config_data["buttons"] = copy.deepcopy(pdata.get("buttons", FACTORY_DEFAULT_BUTTONS.copy()))
    config_data["encoder"] = copy.deepcopy(pdata.get("encoder", {"turn": "general_volume"}))
    config_data["page_names"] = copy.deepcopy(pdata.get("page_names", {}))
    config_data["screen_bg"] = pdata.get("screen_bg", "")
    return config_data

def load_config():
    state.FIRST_RUN = not os.path.exists(CONFIG_FILE) and not os.path.exists(CONFIG_FILE + ".bak")
    default_cfg = {
        "language": "tr", "last_port": "", "accent_color": "#3B82F6", 
        "run_in_bg": False, "start_with_win": False, "auto_connect": True, "screen_bg": "", 
        "show_system_log_menu": False,
        "web_auto_start": False, "web_private_log": False, "web_known_only": False,
        "key_send_mode": "auto", "last_port_serial": "", "device_names": {},
        "ui_mode": "modern", "ui_theme": {},
        "update_check": True,
        # 2.7.0: web modu tuş düzeni ve ekstra ses tekerlekleri
        "web_layout": "device", "web_grid": {"cols": 4, "rows": 3, "pages": 2}, "extra_wheels": [],  # 2.6.4: günde bir GitHub'dan yeni sürüm kontrolü
        "app_mode": "device",  # 2.6: "device" = NexDeck ile, "web" = cihazsız (telefon sanal NexDeck)
        "known_web_devices": {}, "web_access_history": [],
        "mobile_pin": "", "web_token": "", "logged_in_email": "",
        "encoder": {"turn": "general_volume"},
        "page_names": {},
        "buttons": FACTORY_DEFAULT_BUTTONS.copy(),
        "active_profile": DEFAULT_PROFILE_NAME,
        "profiles": {}
    }
    data = _read_config_file_safely()
    for k, v in data.items():
        if isinstance(v, dict) and isinstance(default_cfg.get(k), dict) and k not in ["buttons", "profiles"]:
            default_cfg[k].update(v)
        else:
            default_cfg[k] = v

    # Eski sürümlerde PIN içeren web adresi config'e yazılıyordu; artık gerek yok.
    default_cfg.pop("mobile_url", None)
    if isinstance(default_cfg.get("web_access_history"), list):
        default_cfg["web_access_history"] = default_cfg["web_access_history"][:WEB_HISTORY_LIMIT]

    if not default_cfg.get("web_token"):
        default_cfg["web_token"] = secrets.token_urlsafe(8)

    if "page_names" in default_cfg:
        for _n in ["1", "2", "3", "4"]:
            if default_cfg["page_names"].get(_n) in [f"Sayfa {_n}", f"Page {_n}"]:
                default_cfg["page_names"].pop(_n, None)

    # Eski tek-config kullanıcılarını profile taşı.
    if not default_cfg.get("profiles"):
        default_cfg["profiles"] = {
            default_cfg.get("active_profile", DEFAULT_PROFILE_NAME): snapshot_profile_data(default_cfg)
        }

    ensure_profiles(default_cfg, update_active=False)
    apply_active_profile(default_cfg)

    state.APP_CONFIG = default_cfg
    return default_cfg

def save_config(config_data):
    """
    Atomik kayıt: önce geçici dosyaya yazılır, sonra tek hamlede değiştirilir.
    Böylece yazma sırasında uygulama kapanırsa / iki thread aynı anda kaydederse
    config.json bozulmaz. Önceki sağlam kopya config.json.bak olarak tutulur.
    """
    with CONFIG_LOCK:
        ensure_profiles(config_data, update_active=True)
        state.APP_CONFIG = config_data
        tmp_path = CONFIG_FILE + ".tmp"
        try:
            payload = json.dumps(config_data, indent=4, ensure_ascii=False)
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
            if os.path.exists(CONFIG_FILE):
                try:
                    shutil.copy2(CONFIG_FILE, CONFIG_BACKUP_FILE)
                except Exception:
                    pass
            os.replace(tmp_path, CONFIG_FILE)
        except Exception as e:
            write_error_log("Config kaydedilemedi:\n" + traceback.format_exc())
            ui_log(f"⚠️ Ayarlar kaydedilemedi: {e}")


def _read_config_file_safely():
    """config.json okunamazsa yedekten döner; bozuk dosyayı silmez, yanına kopyalar."""
    for path in (CONFIG_FILE, CONFIG_BACKUP_FILE):
        if not os.path.exists(path):
            continue
        try:
            # utf-8-sig: Not Defteri ile düzenlenip BOM eklenmiş dosyalar da okunur.
            with open(path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            if isinstance(data, dict):
                if path == CONFIG_BACKUP_FILE:
                    ui_log("⚠️ config.json okunamadı; son yedekten (config.json.bak) geri yüklendi.")
                return data
        except Exception:
            write_error_log(f"Config okunamadı: {path}\n" + traceback.format_exc())
            if path == CONFIG_FILE:
                try:
                    shutil.copy2(CONFIG_FILE, CONFIG_FILE + f".corrupt-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
                except Exception:
                    pass
    return {}

def format_action_details(action):
    """Kullanıcının atanmış görevin detayını hatırlaması için kısa açıklama üretir."""
    if not isinstance(action, dict):
        return ""

    atype = action.get("type", "")
    browser = action.get("browser", "")
    app_action = action.get("app_action", "")
    custom_arg = str(action.get("custom_arg", "") or "").strip()
    cmd = str(action.get("cmd", "") or "").strip()

    if atype in ["custom_web", "web"]:
        target = custom_arg or cmd
        if target:
            suffix = f" • {browser}" if browser and browser != "default" else ""
            return f"{target}{suffix}"

    if atype == "custom_app":
        if custom_arg:
            mode_map = {"open": "Aç", "close": "Kapat", "force_close": "Zorla kapat"}
            return f"{mode_map.get(app_action, app_action or 'Aç')} • {custom_arg}"

    if atype == "custom_hotkey":
        if custom_arg:
            return custom_arg

    if atype == "type_text":
        if custom_arg:
            preview = custom_arg.replace("\n", " ")
            return preview[:60] + ("..." if len(preview) > 60 else "")

    if atype == "nircmd":
        if cmd:
            return cmd

    if atype == "cmd":
        if cmd:
            return cmd

    if atype == "native":
        vk = action.get("vk")
        if vk:
            return f"VK: {vk}"

    if atype == "profile":
        mode = action.get("mode", "")
        if mode == "switch":
            return f"Profil: {custom_arg}" if custom_arg else "Profil seçilmedi"
        return {"next": "Sonraki profil", "prev": "Önceki profil"}.get(mode, "")

    return ""

def format_assignment_label(cfg):
    if not isinstance(cfg, dict):
        return ""
    name = cfg.get("name", "") or ""
    details = cfg.get("details", "")
    if not details:
        details = format_action_details(cfg.get("action", {}))
    if details:
        return f"{name} — {details}"
    return name

def execute_macro(action, droppable=True):
    """Görevi makro kuyruğuna ekler; arayüzü bekletmez."""
    if not isinstance(action, dict) or not action.get("type"):
        return
    TASK_WORKER.submit(_execute_macro_now, copy.deepcopy(action), droppable=droppable)


def _run_plugin_action(action):
    plugin_name = action.get("plugin_name")
    plugin = state.LOADED_PLUGINS.get(plugin_name)
    if not plugin:
        ui_log(f"⚠️ Eklenti bulunamadı veya yüklenemedi: {plugin_name}")
        return
    module = plugin["module"]
    if not hasattr(module, "execute"):
        ui_log(f"⚠️ Eklentide execute() fonksiyonu yok: {plugin_name}")
        return

    def _runner():
        started = time.monotonic()
        try:
            module.execute(action.get("function"))
        except Exception as e:
            write_error_log(f"Eklenti hatası ({plugin_name}):\n" + traceback.format_exc())
            ui_log(f"⚠️ Eklenti hatası ({plugin_name}): {e}")
            return
        elapsed = time.monotonic() - started
        if elapsed > 2:
            ui_log(f"🐢 Eklenti yavaş çalıştı ({plugin_name}): {elapsed:.1f} sn")

    # Eklentiler kendi thread'inde çalışır; yavaş/donan bir eklenti diğer tuşları bekletmez.
    threading.Thread(target=_runner, name=f"Plugin-{plugin_name}", daemon=True).start()


def _send_hotkey_via_device(vk_list):
    """Cihaz 'USB klavye' modunu destekliyorsa tuşları gerçek donanım klavyesi gibi gönderir."""
    window = state.MAIN_WINDOW
    if window is None or not getattr(window, "device_supports_hid", False):
        return False
    mode = state.APP_CONFIG.get("key_send_mode", "auto")
    if mode == "software":
        return False
    codes = [HID_KEY_CODES.get(vk) for vk in vk_list]
    if not codes or any(c is None for c in codes):
        return False
    thread = getattr(window, "serial_thread", None)
    if not thread or not thread.is_running:
        return False
    thread.send_data("HID:" + ",".join(str(c) for c in codes) + "\n")
    return True


def _browser_exe(name):
    """2.7.3: Windows 'App Paths' kaydından tarayıcının tam yolu (chrome.exe, msedge.exe, firefox.exe)."""
    if not name:
        return ""
    try:
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(hive, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths" + "\\" + name) as k:
                    path = winreg.QueryValue(k, None)
                    if path and os.path.exists(path.strip('"')):
                        return path.strip('"')
            except OSError:
                pass
    except ImportError:
        pass
    return ""


def _execute_macro_now(action):
    try:
        if action["type"] == "native":
            if not _send_hotkey_via_device([action["vk"]]):
                press_key(action["vk"])
        elif action["type"] == "profile":
            run_on_ui(lambda: state.MAIN_WINDOW and state.MAIN_WINDOW.handle_profile_action(action))
        elif action["type"] == "cmd":
            subprocess.Popen(action["cmd"], shell=True, creationflags=0x08000000)
        elif action["type"] == "ps":
            subprocess.Popen(["powershell", "-Command", action["cmd"]], creationflags=0x08000000)
        elif action["type"] == "nircmd" and os.path.exists(NIRCMD_PATH):
            subprocess.Popen([NIRCMD_PATH] + action["cmd"].split(), creationflags=0x08000000)
        elif action["type"] in ["web", "custom_web"]:
            browser = action.get("browser", "default")
            url = action.get("cmd", "") if action["type"] == "web" else action.get("custom_arg", "")
            if not url.startswith("http"): url = "https://" + url
            
            # 2.7.3: adres kabuğa (cmd) verilmez; tarayıcı App Paths kaydından bulunup argüman listesiyle açılır
            exe = _browser_exe({"chrome": "chrome.exe", "edge": "msedge.exe", "firefox": "firefox.exe"}.get(browser, ""))
            if exe: subprocess.Popen([exe, url], creationflags=0x08000000)
            else: webbrowser.open(url)
            
        elif action["type"] == "custom_app":
            app_path = action.get("custom_arg", "")
            app_action = action.get("app_action", "open")
            if app_action == "open":
                os.startfile(app_path)
            elif app_action == "close":
                subprocess.Popen(f'taskkill /IM "{os.path.basename(app_path)}" /T', shell=True, creationflags=0x08000000)
            elif app_action == "force_close":
                subprocess.Popen(f'taskkill /IM "{os.path.basename(app_path)}" /F /T', shell=True, creationflags=0x08000000)
        elif action["type"] == "type_text":
            if HAS_KEYBOARD:
                keyboard.write(action.get("custom_arg", ""), delay=0.01)
        elif action["type"] == "custom_hotkey":
            keys = [k.strip().lower() for k in action.get("custom_arg", "").split("+")]
            vk_list = [VK_MAP[k] for k in keys if k in VK_MAP]
            unknown = [k for k in keys if k and k not in VK_MAP]
            if unknown:
                ui_log(f"⚠️ Tanınmayan tuş adı: {', '.join(unknown)}")
            if vk_list and not _send_hotkey_via_device(vk_list):
                send_key_combo(vk_list)
        elif action["type"] == "plugin":
            _run_plugin_action(action)
    except Exception as e:
        write_error_log("Makro hatası:\n" + traceback.format_exc())
        ui_log(f"⚠️ Makro Hatası: {str(e)}")

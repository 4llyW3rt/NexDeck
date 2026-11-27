# NexStudio — NEXSTUDIO ÖZGÜR YAZILIM LİSANSI (NPL-v2), Telif Hakkı (c) 2026 Ali Mert Taşcı / NexHub. Ayrıntılar: LICENSE.txt
"""
Modüller arasında paylaşılan ve çalışırken değişen değerler.
Her yerde `state.X` olarak kullanılır (from ... import X ile kopyalanırsa güncel değeri görülmez).
"""
import importlib

MAIN_WINDOW = None        # NexHubApp örneği
APP_CONFIG = {}           # config.json içeriği (MAIN_WINDOW.config ile aynı nesne)
TRANSLATIONS = {}         # dil -> {anahtar: metin}
UI_BRIDGE = None          # arka thread -> arayüz köprüsü
LOADED_PLUGINS = {}       # eklenti adı -> {"actions", "module", "file"}
_SINGLE_INSTANCE_HANDLE = None
FIRST_RUN = False         # 2.6: config.json yoktu (ilk kurulum) -> karşılama ekranı
PLUGIN_LANGUAGES = {}     # 2.6: eklentilerin eklediği diller: kod -> {name, ui, core}


def lazy(module, name):
    """İleri bağımlılık: nexstudio.<module>.<name> değerini ilk kullanımda döndürür."""
    return getattr(importlib.import_module(f"nexstudio.{module}"), name)

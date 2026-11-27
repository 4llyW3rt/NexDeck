"""
Testler için yardımcı: nexstudio paketinin tüm modüllerini tek bir ad alanı gibi gösterir.
  m.NexHubApp, m.save_config, m.TASK_WORKER ...  -> ilgili modülden okunur
  m.LOADED_PLUGINS, m.APP_CONFIG ...             -> state modülünden
  m.execute_macro = sahte                         -> fonksiyonu kullanan TÜM modüllerde değiştirilir
"""
import importlib

MODULES = ["state", "core", "i18n", "engine", "webserver", "serial_link", "app_api", "classic_widgets", "classic_app", "main"]


class _Namespace:
    def __init__(self):
        object.__setattr__(self, "_mods", [importlib.import_module(f"nexstudio.{n}") for n in MODULES])

    def __getattr__(self, name):
        for mod in self._mods:
            if hasattr(mod, name):
                return getattr(mod, name)
        raise AttributeError(name)

    def __setattr__(self, name, value):
        hit = False
        for mod in self._mods:
            if hasattr(mod, name):
                setattr(mod, name, value)
                hit = True
        if not hit:
            raise AttributeError(name)


def load():
    return _Namespace()

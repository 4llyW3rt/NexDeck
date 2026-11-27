# plugins/ornek_eklenti.py
PLUGIN_NAME = "Klasör Kısayolları"

ACTIONS = {
    "İndirilenler Klasörünü Aç": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "open_downloads"},
    "Belgeler Klasörünü Aç": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "open_documents"}
}

def execute(function_name):
    import os
    if function_name == "open_downloads":
        os.startfile(os.path.join(os.path.expanduser('~'), 'Downloads'))
    elif function_name == "open_documents":
        os.startfile(os.path.join(os.path.expanduser('~'), 'Documents'))

"""
Almanca dil eklentisini (src/plugins/dil_deutsch.py) üretir.
Kaynak: src/web_ui/lang/en.json (Türkçe -> İngilizce) + tools/i18n/de_from_en.json (İngilizce -> Almanca).
Arayüze yeni metin eklenince: önce en.json'a, sonra de_from_en.json'a ekleyip bu aracı çalıştırın.
Eksik Almanca varsa liste halinde yazar ve dosyayı değiştirmez.

Kullanım:  python tools/build_lang_plugin.py
"""
import json, os, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
EN = json.load(open(os.path.join(ROOT, "src", "web_ui", "lang", "en.json"), encoding="utf-8"))["ui"]
DE = json.load(open(os.path.join(ROOT, "tools", "i18n", "de_from_en.json"), encoding="utf-8"))
OUT = os.path.join(ROOT, "src", "plugins", "dil_deutsch.py")

missing = sorted({v for v in EN.values() if v not in DE})
if missing:
    print("Eksik Almanca çeviriler (tools/i18n/de_from_en.json'a ekleyin):")
    print(json.dumps(missing, ensure_ascii=False, indent=1))
    sys.exit(1)

ui = {tr_key: DE[en_val] for tr_key, en_val in EN.items()}
body = json.dumps(ui, ensure_ascii=False, indent=8)
with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write(f'''# NexStudio dil eklentisi örneği: Almanca (Deutsch)
# Bir eklenti sadece LANGUAGES tanımlayarak yeni dil ekleyebilir (ACTIONS gerekmez).
# Biçim: {{"dil_kodu": {{"name": "Görünen ad", "ui": {{Türkçe metin: çeviri}}, "core": {{klasik görünüm anahtarı: çeviri}}}}}}
# "core" boş bırakılırsa klasik görünüm ve görev adları İngilizce görünür.
# Kendi dilini eklemek için bu dosyayı kopyalayıp çevirileri değiştirmen yeterli.
# (Bu dosya tools/build_lang_plugin.py ile üretilir.)

LANGUAGES = {{
    "de": {{
        "name": "Deutsch",
        "ui": {body},
        "core": {{}},
    }}
}}
''')
print("ok", len(ui), "metin")

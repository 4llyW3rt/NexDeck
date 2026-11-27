"""en.json ve de_from_en.json'u günceller: yeni metinleri ekler, eskiyen anahtarları kaldırır.
Kullanım: python i18n_update.py <repo> <updates.json>
updates.json: {"add": {tr: [en, de]}, "remove": [tr, ...]}"""
import json, os, sys
repo, upd_path = sys.argv[1], sys.argv[2]
upd = json.load(open(upd_path, encoding="utf-8"))
en_path = os.path.join(repo, "src", "web_ui", "lang", "en.json")
de_path = os.path.join(repo, "tools", "i18n", "de_from_en.json")
en = json.load(open(en_path, encoding="utf-8"))
de = json.load(open(de_path, encoding="utf-8"))
for k in upd.get("remove", []):
    en["ui"].pop(k, None)
for tr_text, (en_text, de_text) in upd.get("add", {}).items():
    en["ui"][tr_text] = en_text
    de[en_text] = de_text
json.dump(en, open(en_path, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=2)
json.dump(de, open(de_path, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
print("en:", len(en["ui"]), "de:", len(de))

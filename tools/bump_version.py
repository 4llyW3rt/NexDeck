"""
Sürüm yükseltme aracı.
  - src/nexstudio/core.py: APP_VERSION, NEXSTUDIO_BUILD_ID, NEXSTUDIO_BUILD_CHANNEL, uygulama içi "Yenilikler" (tr/en)
  - installer/NexStudio_Setup.iss: sürüm ve kurulum dosyası adı
Kullanım:
  python tools/bump_version.py 2.6.1 notes.json
notes.json: {"date_tr": "28.11.2026", "date_en": "2026-11-28", "tr": ["madde", ...], "en": ["item", ...]}
Not: 3.0.0'a geçilmez (3.0 internete bağlı hesap sürümü için ayrıldı).
"""
import json, os, re, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
version, notes_path = sys.argv[1], sys.argv[2]
if not re.fullmatch(r"2\.\d+\.\d+", version):
    raise SystemExit("Sürüm 2.x.y biçiminde olmalı (3.0 ayrılmış).")
notes = json.load(open(notes_path, encoding="utf-8"))
short = version[:-2] if version.endswith(".0") else version  # 2.7.0 -> "2.7"

core = os.path.join(ROOT, "src", "nexstudio", "core.py")
s = open(core, encoding="utf-8").read()
s = re.sub(r'APP_VERSION = "[^"]+"', f'APP_VERSION = "{version}"', s, count=1)
s = re.sub(r'NEXSTUDIO_BUILD_ID = "[^"]+"', f'NEXSTUDIO_BUILD_ID = "NEX-{version.replace(".", "")}-AMT"', s, count=1)
s = re.sub(r'NEXSTUDIO_BUILD_CHANNEL = "[^"]+"', f'NEXSTUDIO_BUILD_CHANNEL = "Public {".".join(version.split(".")[:2])}"', s, count=1)


def entry(lang, date, items):
    body = "".join(f"            {json.dumps(i, ensure_ascii=False)},\n" for i in items)
    return f'        ("{short}", "{date}", [\n{body}        ]),\n'


for lang, date in (("tr", notes["date_tr"]), ("en", notes["date_en"])):
    anchor = f'    "{lang}": [\n'
    idx = s.index("NEXSTUDIO_CHANGELOG = {")
    pos = s.index(anchor, idx) + len(anchor)
    if f'("{short}", ' in s[pos:pos + 200]:
        raise SystemExit(f"{short} zaten var ({lang})")
    s = s[:pos] + entry(lang, date, notes[lang]) + s[pos:]
open(core, "w", encoding="utf-8", newline="\n").write(s)

iss = os.path.join(ROOT, "installer", "NexStudio_Setup.iss")
t = open(iss, encoding="utf-8").read()
t = re.sub(r'#define MyAppVersion "[^"]+"', f'#define MyAppVersion "{version}"', t)
t = re.sub(r"OutputBaseFilename=NexStudio_Setup_[\d_]+", f"OutputBaseFilename=NexStudio_Setup_{version.replace('.', '_')}", t)
open(iss, "w", encoding="utf-8").write(t)
print("sürüm:", version)

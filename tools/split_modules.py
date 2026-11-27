"""
Tek dosyalık nexstudio_ui.py'yi src/nexstudio/ paketine böler (2.5.1).
Bir kez çalıştırılan geliştirici aracıdır; sonucu git'te durur.

- Modüller arasında yeniden atanan 6 değişken (MAIN_WINDOW, APP_CONFIG, ...) state.py'ye taşınır
  ve her yerde state.X olarak kullanılır.
- Her modülün diğer modüllerden kullandığı isimler AST ile bulunur ve açık import satırları üretilir.
Kullanım:  python tools/split_modules.py src/nexstudio_ui.py src/nexstudio  [--report]
"""
import ast, builtins, os, re, sys

SRC, OUT = sys.argv[1], sys.argv[2]
REPORT = "--report" in sys.argv
STATE_NAMES = ["MAIN_WINDOW", "APP_CONFIG", "TRANSLATIONS", "UI_BRIDGE", "LOADED_PLUGINS", "_SINGLE_INSTANCE_HANDLE"]
lines = open(SRC, encoding="utf-8").read().split("\n")


def find(pattern, start=0):
    for i in range(start, len(lines)):
        if re.match(pattern, lines[i]):
            return i
    raise SystemExit("bulunamadı: " + pattern)


def header_start(title_regex):
    i = find(r"^# " + title_regex)
    return i - 1  # üstteki "# ====" satırı


license_end = find(r"^import sys$")
b_core = license_end
b_i18n = header_start(r"3\. DİL SİSTEMİ")
b_engine = header_start(r"4\. WINDOWS API")
b_web = header_start(r"5\. MOBİL SUNUCU")
b_serial = header_start(r"6\. SERİ PORT")
b_widgets = header_start(r"7\. ARAYÜZ")
b_app = find(r"^class NexHubApp\(QMainWindow\):")
b_api = header_start(r"8\. YENİ ARAYÜZ")
b_main = find(r'^if __name__ == "__main__":')

# Sıra önemli: her modül sadece kendinden öncekilerden import eder.
MODULES = [
    ("core", b_core, b_i18n, "Temel altyapı: kütüphaneler, dosya yolları, log, görev kuyruğu, SendInput tuş gönderimi, tek kopya."),
    ("i18n", b_i18n, b_engine, "Dil sistemi: varsayılan çeviriler, dil dosyaları, tr()."),
    ("engine", b_engine, b_web, "Görev motoru: tuş/sinyal tanımları, hazır görevler, eklentiler, profiller, ayar dosyası, execute_macro."),
    ("webserver", b_web, b_serial, "Telefondan kontrol (LAN) web sunucusu: PIN, tanınan cihazlar, eski web arayüzü."),
    ("serial_link", b_serial, b_widgets, "Arduino ile seri haberleşme (SerialThread)."),
    ("app_api", b_api, b_main, "Yeni arayüzün yerel API'si (AppApi), yerel sunucu ve arayüz penceresi işlemi."),
    ("classic_widgets", b_widgets, b_app, "Klasik (PyQt) görünüm: stil sayfası ve özel bileşenler."),
    ("classic_app", b_app, b_api, "Ana uygulama sınıfı NexHubApp: cihaz bağlantısı, profiller, tray, klasik pencere."),
]

state_re = re.compile(r"(?<![\w.])(" + "|".join(STATE_NAMES) + r")\b")


def transform(text):
    out = []
    for ln in text.split("\n"):
        s = ln.strip()
        if s.startswith("global ") and all(n.strip() in STATE_NAMES for n in s[7:].split(",")):
            continue
        out.append(state_re.sub(r"state.\1", ln))
    return "\n".join(out)


def top_defs(tree):
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                for n in ast.walk(t):
                    if isinstance(n, ast.Name):
                        names.add(n.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                names.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, (ast.Try, ast.If)):
            # try: import x / if ...: bloklarındaki tanımlar
            for sub in ast.walk(node):
                if isinstance(sub, (ast.Import, ast.ImportFrom)):
                    for a in sub.names:
                        names.add((a.asname or a.name).split(".")[0])
                elif isinstance(sub, ast.Assign):
                    for t in sub.targets:
                        if isinstance(t, ast.Name):
                            names.add(t.id)
                elif isinstance(sub, (ast.FunctionDef, ast.ClassDef)):
                    names.add(sub.name)
    return names


def used_names(tree):
    used = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
            used.add(n.id)
    return used


BUILTINS = set(dir(builtins)) | {"__file__", "__name__"}
bodies, defs, uses = {}, {}, {}
for name, a, b, _ in MODULES:
    body = transform("\n".join(lines[a:b]))
    tree = ast.parse(body)
    bodies[name], defs[name], uses[name] = body, top_defs(tree), used_names(tree)

main_body = transform("\n".join(lines[b_main + 1:]))
main_tree = ast.parse("def main():\n" + main_body)
uses["main"] = used_names(main_tree)
defs["main"] = set()
order = [m[0] for m in MODULES] + ["main"]

ALL_DEFS = set().union(*defs.values())
imports, problems = {}, []
for idx, name in enumerate(order):
    # Sadece bir modülde üst düzeyde tanımlı isimler; geri kalanlar fonksiyonların yerel değişkenleridir.
    need = (uses[name] & ALL_DEFS) - defs[name] - BUILTINS - {"state"}
    by_mod = {}
    for n in sorted(need):
        src = None
        for prev in reversed(order[:idx]):
            if n in defs[prev]:
                src = prev
                break
        if src:
            by_mod.setdefault(src, []).append(n)
        else:
            later = [m for m in order[idx + 1:] if n in defs[m]]
            problems.append((name, n, later))
    imports[name] = by_mod

if REPORT or problems:
    for name, n, later in problems:
        print(f"İLERİ/EKSİK: {name} -> {n}  (tanım: {later or 'YOK'})")
    if REPORT:
        for name in order:
            print(name, {k: len(v) for k, v in imports[name].items()})
        sys.exit(0)

LAZY = {}  # modül -> {isim: kaynak_modül}  (ileri bağımlılıklar fonksiyon içinde çözülür)
for name, n, later in problems:
    if not later:
        raise SystemExit(f"Tanımı olmayan isim: {name} -> {n}")
    LAZY.setdefault(name, {})[n] = later[0]

os.makedirs(OUT, exist_ok=True)
LICENSE = "# NexStudio — NEXSTUDIO ÖZGÜR YAZILIM LİSANSI (NPL-v2), Telif Hakkı (c) 2026 Ali Mert Taşcı / NexHub. Ayrıntılar: LICENSE.txt\n"


def import_block(name):
    out = ["from . import state"]
    for src, names in imports[name].items():
        out.append(f"from .{src} import (  # noqa: F401\n    " + ",\n    ".join(names) + ",\n)")
    return "\n".join(out)


# core: bu dosya artık src/nexstudio/ içinde; geliştirme modunda kaynaklar (ikon, web_ui, eklentiler) src/ altında
_old_res = "return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)"
assert _old_res in bodies["core"], "get_resource_path bulunamadı"
bodies["core"] = bodies["core"].replace(
    _old_res, "return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), relative_path)")

for name, a, b, doc in MODULES:
    body = bodies[name]
    for n, src in LAZY.get(name, {}).items():
        body = re.sub(rf"(?<![\w.]){n}\b", f"_lazy('{src}', '{n}')", body)
    head = [LICENSE, f'"""{doc}"""']
    if name == "core":
        head.append("# flake8: noqa")
    head.append(import_block(name) if name != "core" else "from . import state")
    if name in LAZY:
        head.append("from .state import lazy as _lazy")
    with open(os.path.join(OUT, f"{name}.py"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(head) + "\n\n" + body.strip("\n") + "\n")

with open(os.path.join(OUT, "state.py"), "w", encoding="utf-8", newline="\n") as f:
    f.write(LICENSE + '''"""
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


def lazy(module, name):
    """İleri bağımlılık: nexstudio.<module>.<name> değerini ilk kullanımda döndürür."""
    return getattr(importlib.import_module(f"nexstudio.{module}"), name)
''')

main_imports = import_block("main")
with open(os.path.join(OUT, "main.py"), "w", encoding="utf-8", newline="\n") as f:
    # Gövde zaten 4 boşlukla girintili (eski `if __name__ == "__main__":` bloğu)
    f.write(LICENSE + '"""Uygulamanın giriş noktası."""\n' + main_imports + "\n\n\ndef main():\n" + main_body.strip("\n") + "\n")

with open(os.path.join(OUT, "__init__.py"), "w", encoding="utf-8", newline="\n") as f:
    f.write(LICENSE + '"""NexStudio paketi. Modül sırası: core > i18n > engine > webserver > serial_link > app_api > classic_widgets > classic_app > main"""\n')
print("ok", {k: sum(len(v) for v in imports[k].values()) for k in order}, "lazy:", LAZY)

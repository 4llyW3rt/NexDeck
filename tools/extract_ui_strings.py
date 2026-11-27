"""
Yeni arayüzdeki (src/web_ui/app.html) çevrilecek Türkçe metinleri çıkarır.
Kullanım:  python tools/extract_ui_strings.py [dil_dosyası.json]
Dil dosyası verilirse sadece EKSİK metinleri yazdırır (çevirmenler için).
"""
import json, re, sys, os

HTML = os.path.join(os.path.dirname(__file__), "..", "src", "web_ui", "app.html")
src = open(HTML, encoding="utf-8").read()
src = re.sub(r"<style>.*?</style>", "", src, flags=re.S)
TR = re.compile(r"[çğıöşüÇĞİÖŞÜ]|\b(ve|bir|ile|için|yok|var|gibi|Sil|Profil|Tuş|Kopyala|Kapat|Dene|Bağlan|Ayarlar|Telefon|Cihaz|Görev|Ses|Tema|Koyu|Açık|Genel|Dil|Sürüm|Başlat|Durdur|Boş|Sayfa|Yeni|Kontrol|Düzenle)\b")


def norm(s):
    s = re.sub(r"\s+", " ", s).strip()
    return s


found = []


def add(s):
    s = norm(s)
    if len(s) < 2 or not TR.search(s) or s.startswith(("http", "#", ".", "/")):
        return
    if re.fullmatch(r"[\W\d_]+", s):
        return
    if s not in found:
        found.append(s)


# 1) JS string literalleri ("..." ve '...')
for m in re.finditer(r'"((?:[^"\\\n]|\\.)*)"|\'((?:[^\'\\\n]|\\.)*)\'', src):
    s = m.group(1) if m.group(1) is not None else m.group(2)
    if "<" in s:
        for part in re.split(r"<[^>]*>", s):
            add(part)
    else:
        add(s)

# 2) Şablon metinleri (`...`): ${...} -> {0}, {1}; etiketler arasındaki parçalar ayrı metindir
for m in re.finditer(r"`((?:[^`\\]|\\.)*)`", src, flags=re.S):
    body = m.group(1)
    for part in re.split(r"<[^>]*>", body):
        idx = [0]

        def ph(_):
            i = idx[0]; idx[0] += 1
            return "{%d}" % i
        cleaned = re.sub(r"\$\{(?:[^{}]|\{[^{}]*\})*\}", ph, part)
        # sadece yer tutucu + noktalama kalan parçaları ve içinde JS olanları atla
        if re.search(r"[=;()?]|=>", cleaned) and not TR.search(re.sub(r"\{\d\}", "", cleaned)):
            continue
        add(cleaned)

# 3) HTML metni ve öznitelikler
for m in re.finditer(r">([^<>`${}]+)<", src):
    add(m.group(1))
for m in re.finditer(r'(?:placeholder|title|aria-label)="([^"]+)"', src):
    add(m.group(1))

found = [s for s in found if not re.search(r"\b(const|function|return|document|=>)\b", s)]
if len(sys.argv) > 1:
    have = json.load(open(sys.argv[1], encoding="utf-8")).get("ui", {})
    found = [s for s in found if s not in have]
print(json.dumps(found, ensure_ascii=False, indent=1))
print(len(found), "metin", file=sys.stderr)

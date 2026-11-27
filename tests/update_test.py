"""
2.6.4 güncelleme testi (gerçek GitHub'a karşı, kurulum YAPMAZ):
çekirdeği "eski sürümmüş gibi" (NEXSTUDIO_FAKE_VERSION) başlatır; yeni sürümü bulmasını, indirip SHA-256 ile doğrulamasını
ve SHA tutmazsa dosyayı reddetmesini kontrol eder.
Kullanım:  python tests/update_test.py <src klasörü> <geçici veri klasörü>
"""
import json, os, sys, time, urllib.request

SRC, DATA = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
os.environ.update(NEXSTUDIO_DATA_DIR=DATA, NEXSTUDIO_FAKE_VERSION="2.6.0", QT_QPA_PLATFORM="offscreen")
os.makedirs(DATA, exist_ok=True)
sys.path.insert(0, SRC)
from nexstudio import updater  # noqa: E402

results = []


def check(name, cond):
    results.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name)


st = updater.check(manual=True)
check(f"yeni sürüm bulundu ({st.get('latest')} > {st.get('current')})", st["state"] == "available")
check("kaynaktan çalışırken kurulum kapalı", st["can_install"] is False)
info = dict(updater._INFO)
check("indirme adresi sadece bu deponun resmi adresi", info["exe_url"].startswith(updater.ALLOWED_PREFIX))
path = updater.download_and_verify()
check("indirildi ve SHA-256 doğrulandı", os.path.exists(path) and updater.status()["state"] == "ready")
size = os.path.getsize(path)
check(f"dosya boyutu makul ({size // 1024 // 1024} MB)", size > 10 * 1024 * 1024)

# Yanlış doğrulama kodu: dosya kurulmamalı ve silinmeli
orig_download = updater._download


def fake_download(url, dest):
    if url.endswith(".sha256"):
        with open(dest, "w") as f:
            f.write("0" * 64 + "  sahte\n")
        return dest
    return orig_download(url, dest)


updater._download = fake_download
try:
    updater.download_and_verify()
    check("SHA tutmayan dosya reddedilir", False)
except ValueError as e:
    check("SHA tutmayan dosya reddedilir ve silinir", "doğrulanamadı" in str(e) and not os.path.exists(path))
updater._download = orig_download

# Güvenilmeyen adres
try:
    updater._download("https://example.com/kotu.exe", os.path.join(DATA, "x.exe"))
    check("başka adresten indirme engellenir", False)
except ValueError:
    check("başka adresten indirme engellenir", True)

print(f"\n{sum(results)}/{len(results)} geçti")
sys.exit(0 if all(results) else 1)

# NexStudio Değişiklik Günlüğü

Bu dosya, NexStudio masaüstü uygulamasında ve NexDeck firmware'inde yapılan değişiklikleri kaydeder.
Uygulama içindeki "Güncelleme Rehberi" kartı da aynı bilgiyi kısaca gösterir (`NEXSTUDIO_CHANGELOG`, `src/nexstudio_ui.py`).

---

## 2.8.0 — 27.11.2026 (Ebeveyn kontrolü)

### Özellik
- Ayarlar > Genel > "Ebeveyn kontrolü" kenar çubuğuna **Ebeveyn** bölümünü ekler (`parental_ui` ayarı).
- `parental.py`: PBKDF2 ebeveyn şifresi, tek seferlik gösterilen kurtarma kodu (`XXXX-XXXX-XXXX-XXXX`), günlük süre
  (yalnızca biri başındayken sayılır; 2 dk boşta kalınca durur), kullanım saatleri (gece yarısını aşabilir; başlangıç = bitiş: sınırsız),
  ek süre, 30 dk yönetici oturumu (`time.monotonic`: saati geri almak uzatmaz), 5 yanlış şifreden sonra 60 sn bekleme.
- `parental_ui.py` (Qt): her ekranı kaplayan, en üstte duran kilit penceresi; kilitte kullanıcının pencereli programları kapatılır
  (Windows klasöründeki kabuk/sistem işlemleri ve NexStudio'nun kendi işlemleri hariç; UWP uygulamaları da), Win / Alt+Tab / Alt+Esc /
  Ctrl+Esc / Ctrl+Shift+Esc düşük seviye klavye kancasıyla engellenir, ekran takılıp çıkarılınca pencereler yeniden kurulur.
  Saat/tarih atlaması (2 dk+) algılanınca "saat değiştirildi" kilidi. Win+L ile yönetici oturumu kapanır (`OpenInputDesktop`/`SwitchDesktop`).
- Kilitliyken `execute_macro` hiçbir görevi çalıştırmaz (NexDeck, telefon). Ebeveyn kontrolü açıkken `force_quit`, tepsi "Çık",
  `/api2/ui quit`, "arka planda çalış" ve "Windows ile başlat" kapatma ebeveyn oturumu ister (güncelleme kurulumu hariç).
- API: `GET/POST /api2/parental` (yalnızca bilgisayardan). Kilit ekranı metinleri `i18n.ui_tr` ile çevrilir.
- Deneme modu `NEXSTUDIO_PARENTAL_DRYRUN=1` yalnızca kaynaktan çalışırken geçerli (kurulu exe'de yok sayılır).

### Nasıl test edildi
agy (Gemini) `tests/parental_test.py`'yi yazdı (56 kontrol, deneme modunda) ve 14 atlatma/hata buldu; uygulama içinde çözülebilenler bu sürümde.

### Bilinen sınırlar (2.8.x'te koruma servisiyle)
- Çocuk yönetici yetkili hesaptaysa Ctrl+Alt+Del > Görev Yöneticisi (yönetici olarak) ile NexStudio'yu kapatabilir ya da
  `%APPDATA%/NexStudio/config.json`'u düzenleyebilir. Çözüm: yönetici yetkisiyle çalışan koruma servisi + ayarların korumalı klasörde tutulması.

---

## 2.7.3 — 27.11.2026 (Telefonda tekerlek/ızgara, güvenlik sertleştirme)

### Nasıl test edildi
Testler Antigravity CLI (Gemini) kopyalarına verildi (Claude yönetici). agy üç paralel görev yürüttü: erişim kontrolü
testleri (`security_regression_test.py`, 95 kontrol), çeviri denetimi ve gerçek tarayıcıyla arayüz testi.
Arayüz testi projeye alındı: `tests/ui_regression_test.py` (yalnızca standart kütüphane + kurulu Edge, CDP; 4 ekran boyutu, 118 kontrol)
ve yayın betiğinde her sürümde çalışır.

### Telefon
- "Düzenle" modunda ekstra tekerlek eklenir/değiştirilir; telefonun Ayarlar sayfasında "Tuş düzeni" (cihazla aynı / serbest ızgara, boyut).
  `post_settings` telefondan yalnızca `web_layout`, `web_grid`, `extra_wheels` anahtarlarını kabul eder.

### Güvenlik
- `is_safe_web_url`: telefondan atanan adres yalnızca http(s), ASCII, geçerli alan adı; `javascript:`, `file:`, tırnak, `% < > ` ^ | \` ve
  Unicode benzeri karakterler reddedilir. Tarayıcı artık `cmd /c start` (shell=True) yerine App Paths kaydındaki exe ile argüman listesiyle açılır.
- Eski `/api/trust_device` kapatıldı: telefon kendine kalıcı "tanınan cihaz" çerezi veremiyordu → artık yalnızca bilgisayardaki onayla.
- Onay modunda IP+tarayıcı eşleşmesi tek başına yeni oturum açtırmaz; onay 15 sn geçerli, sonra çerez gerekir.
- Ham istek yolunda `//`, `..`, `%2e/%2f/%5c` reddedilir; bilinmeyen `/<kod>/...` alt yolları 404.
- Telefon POST: bozuk JSON/UTF-8 400, çok büyük gövde 413 (önceden 500 + hata günlüğü).
- Masaüstü API: `Host` yalnızca `127.0.0.1/localhost:<port>`, `Origin` aynı adres (DNS rebinding / CSRF); çerez tam ad=değer eşleşmesi,
  `secrets.compare_digest`.

### Diğer
- Çeviri: kütüphane araması `L()` ile çevrilmiş adlarda da arar ve aktif dilin küçük harf kuralını kullanır; tekerlek hedefleri,
  "Buraya bırak" (CSS) ve 56 eksik metin çevrildi.
- `set_app_mode("device")` "otomatik bağlan" kapalıyken cihaz aramaz. Dar ekranda Düzen menüsünde "Sol menü" anahtarı gizli (alt çubuk gizlenmez).
  Izgara boyutu seçenekleri "Sütun: 4" biçiminde (tekil/çoğul hatası yok).

---

## 2.7.2 — 27.11.2026 (Telefon güvenliği ve çeviriler)

- **Güvenlik:** `custom_hotkey` ve `type_text` de `_LOCAL_ONLY_TASK_TYPES`'a eklendi. PIN'i bilen biri telefondan
  "win+r" kısayolu ile komut yazdırmayı birleştirip bilgisayarda komut çalıştırabiliyordu. Telefondan atanmış tuşa basmak çalışır;
  telefondaki görev listesinde bu türler gösterilmez.
- **Telefon sayfaları çevrildi** (`webserver._t`): PIN girişi, yanlış PIN/kilit, onay bekleniyor/reddedildi/zaman aşımı,
  engellendi ve "bağlantı kodu değişti" sayfaları aktif dile göre; `<html lang>` doğru.
- **Eklenti ve profil görevleri** İngilizce/Almanca (109 yeni anahtar). Çeviri işini Antigravity CLI (Gemini) yaptı, kontrol ve testler Claude'da.
- Test modunda (`QT_QPA_PLATFORM=offscreen`) arayüz penceresi açılmaz; testler masaüstünde pencere bırakmaz.

---

## 2.7.1 — 27.11.2026 (Çoklu ajan testi düzeltmeleri)

### Nasıl test edildi
Arayüz dört ayrı test ajanına bölündü (düzen/katmanlar, cihaz modu, web/telefon, ayarlar/diller). Her ajan kendi
yalıtılmış çekirdeğini (`NEXSTUDIO_DATA_DIR`) çalıştırıp tarayıcıda baştan sona denedi; bulunan hatalar arayüz,
arka uç, çeviri ve web güvenliği ajanlarına dosya bazında dağıtıldı, son olarak bir doğrulama ajanı hepsini yeniden denedi.

### Arayüz (`app.html`)
- Düzen menüsü panellerin arkasında açılıyordu: üst çubuk `backdrop-filter` yüzünden kendi katmanını açıyor. Katman sırası
  düzenlendi (üst çubuk 35 < Düzen 45 < Yenilikler 50 < karşılama 70 < pencere 80 < onay 90 < bağlantı yok 95 < bildirim 100).
- Düzen menüsü `<body>`'ye taşındı; üst çubuk gizliyken sağ alttaki "Düzen" düğmesi menüyü açar, "Tümünü göster" eklendi.
  Düzen ve Yenilikler aynı anda açık kalmaz, Esc ikisini de kapatır; karşılama ekranındayken F11 çalışmaz.
- `dialog()` içindeki yerel `esc` değişkeni genel HTML kaçış fonksiyonunu gölgeliyordu: seçim listeli her pencere
  (ekstra tekerlek ekle/düzenle) `ReferenceError` ile açılmıyordu.
- Dar pencerede gizlenen sol menü tüm ekranı kaplıyordu; görev listesi/tuş ayarları gizlenince ızgarada boş sütun kalıyordu.
- Açılır pencereler şeffaflık ayarından bağımsız opak; uzun metin (güncelleme notları) kaydırılır, satır sonları korunur.
- Sayfa adı boş bırakılınca varsayılana döner (en fazla 20 karakter); profil adları en fazla 40 karakter;
  başka profili kopyalamak artık önce o profile geçmez (`source`).
- 1. sayfadaki ekran butonlarının numarası yanlıştı (◀ olmayan sayfa).
- "Güncellemeleri otomatik denetle" anahtarı hemen dönmüyordu.
- Serbest ızgara telefonda taşıyordu; Web sayfasında QR'a tıklayınca cihaz listesi güncellenmeyi bırakıyordu; "Sanal" rozeti görünmüyordu.
- Telefonda "Özel Uygulama" görevi listede gösterilmez.

### Arka uç (`app_api.py`)
- Dict olmayan gövde ve tür hataları 500 yerine 400; ayarlar, profil, sayfa adı, tekerlek hedefi, ses adımı ve resim
  girdileri doğrulanıyor (`_SIG_RE`, `is_valid_turn_target`). Yeni test: `tests/api_validation_test.py`.
- Seçilen emoji aynı görevin ayarı değişince korunur.
- Oturum çerezi porta göre adlandırılır (`nex_app_<port>`): iki kopya birbirinin oturumunu kapatmaz.
- Yapılandırma değişiklikleri `CONFIG_LOCK` altında yapılır.

### Web (`webserver.py`)
- "Hatırlanan" cihazlar ayrı bir `TRUST-xxxx` kaydı açıyordu; bu yüzden atma/unutma/engelleme işe yaramıyordu.
  Artık tek kayıt; eski kayıtlar açılışta birleştirilir.
- Eski bağlantı koduyla gelen istekler 401 JSON / açıklayıcı sayfa alır: telefon kilitlenmek yerine yeniden giriş ister.
- "Sadece izin verdiğim cihazlar" açıkken bilgisayardan onaylanan cihaz izinli olur.
- Güvenlik: telefondan `custom_app` ataması reddedilir; uzaktan girilen web adresleri komut enjeksiyonuna karşı denetlenir;
  eski `/api/save` uç noktası da aynı doğrulamadan geçer.
- Yanlış PIN adres çubuğunda kalmaz; cihazlar model adıyla listelenir (ör. "Pixel 8 - Chrome").

### Çeviri
- `L()` en uzun kalıbı önce dener ve yer tutucuları da çevirir; İngilizce → Almanca geçişte sayfa yenilenir;
  ~45 sunucu/güncelleme mesajı eklendi; kullanıcı adları (profil, sayfa) çevrilmez.

### Tarih düzeltmesi
- 2.6.1–2.7.0 sürümleri yanlışlıkla 28.11.2026 tarihli yazılmıştı; doğrusu 27.11.2026.

---

## 2.7.0 — 27.11.2026 (Ekstra ses tekerlekleri, web modu ızgara seçimi)

- **Ekstra ses tekerlekleri** (`config.json > extra_wheels`, en fazla 6): cihazın altında, hem cihazlı hem web modunda.
  Her tekerlek kendi hedefini kontrol eder: genel ses, aktif pencere, parlaklık ya da bir uygulama (`app_volume:Discord.exe`).
  Düzenle modunda "＋ Tekerlek ekle" ve tekerlek üzerindeki "⋯" (hedefi değiştir / kaldır). Telefonda da sürükleyerek çevrilir.
  Çekirdek: ses mantığı `NexHubApp.apply_volume_steps(hedef, adım)` olarak ayrıldı; `/api2/volume` artık `target` alabilir.
- **Web modu tuş düzeni** (`web_layout`): `device` (cihazla aynı, 4 sayfa) ya da `grid` (serbest ızgara, `web_grid`: 2–6 sütun, 1–4 satır,
  1–8 sayfa). Serbest ızgara tuşları `WEB:P{sayfa}_B{n}` sinyalleriyle saklanır; sayfa adları çift tıklayarak değişir.
- Web modunda fiziksel tuş sırası gizlenir.
- Tekerlek kodu `makeKnob()` olarak yeniden kullanılabilir hale getirildi (ana tekerlek + ekstra tekerlekler).
- Diyalog penceresine seçim listesi desteği.
- Düzeltilen hata (yayın öncesi): "Güncelleme var" rozeti `local-only` sınıfı yüzünden güncelleme yokken de görünüyordu.

---

## 2.6.4 — 27.11.2026 (Otomatik güncelleme, yönetici izni istemeyen kurulum)

### Neden
Kurulum `Program Files`'a yapıldığı için her güncellemede Windows yönetici izni (UAC) soruyordu; bu, otomatik
güncellemeyi ve gece kurulumlarını imkânsız kılıyordu.

### Kurulum
- Inno Setup: `PrivilegesRequired=lowest` → `%LOCALAPPDATA%\Programs\NexStudio` (Chrome / Discord / VS Code gibi).
  Kurulum ve güncelleme UAC sormaz. Ayarlar (`%APPDATA%\NexStudio`) aynı yerde kalır.
- `UsePreviousAppDir=no`: eski yönetici kurulumunun yolu kullanılmaz.
- Eski `Program Files` / `Program Files (x86)` kopyası bulunursa Ayarlar'da **Kaldır** kartı çıkar (kaldırıcıyı bir kez yönetici izniyle çalıştırır).

### Otomatik güncelleme (`src/nexstudio/updater.py`)
- Açılıştan 15 sn sonra ve günde bir kez `releases/latest` sorgulanır (hesap/anahtar gerekmez). Ayarlar'dan kapatılabilir.
- Yeni sürüm: üst çubukta "Güncelleme var" rozeti + tray bildirimi; "Neler yeni?" sürüm notlarını gösterir.
- **Güncelle:** kurulum dosyası sadece `https://github.com/4llyW3rt/NexDeck/releases/download/` adresinden indirilir,
  release'teki `.sha256` dosyasıyla doğrulanır (tutmazsa silinir, kurulmaz), NexStudio kapanır, kurulum
  `/VERYSILENT` çalışır ve yeni sürüm açılır.
- Kaynaktan çalışırken sadece indirip doğrular, kurmaz.
- Yayın betiği her sürüme `NexStudio_Setup_x_y_z.exe.sha256` dosyasını ekler (2.6.1'den beri).

### Test
`tests/update_test.py` (gerçek GitHub'a karşı): eski sürüm gibi davranıp yeni sürümü bulma, resmi adres kontrolü,
37 MB indirme + SHA-256 doğrulama, sahte doğrulama kodunun reddi, başka adresten indirmenin engellenmesi — 7/7.

---

## 2.6.3 — 27.11.2026 (Bağlanan cihazlar, engelleme, onay)

### Düzeltilen eksik
Bağlanan cihazlar listede görünmüyordu: cihazı kaydeden `ensure_known_web_device` hiçbir yerden çağrılmıyordu ve
yeni arayüzde "Bu cihazı hatırla" adımı yoktu. Artık bağlanan ya da bağlanmaya çalışan her cihaz kaydedilir.

### Yeni
- **Oturum çerezi:** PIN ya da onaydan sonra cihaza `HttpOnly` oturum çerezi verilir, PIN adres çubuğundan temizlenir
  (302 yönlendirme). Yeni arayüzün API çağrıları artık bu çerezle yetkilenir.
- **Bağlanan cihazlar** (Web sayfası): çevrimiçi olanlar en üstte; Bağlantıyı kes, Engelle / Engeli kaldır, İzin ver / İzni kaldır, Adlandır, Unut.
  "Bağlantıyı kes" oturumu kapatır ve PIN'siz giriş hakkını (tanınma) kaldırır; telefon giriş ekranına düşer.
- **Engelleme:** engellenen cihaz PIN'i bilse de hiçbir sayfaya/API'ye erişemez.
- **Erişim modu** (kullanıcının seçimi): `pin` / `approve` (PIN yok, bilgisayardan onay) / `pin_approve`.
  Onay isteği bilgisayarda geri sayımlı pencerede ve tray bildiriminde görünür; 60 sn içinde cevap yoksa reddedilir.
  "Bu cihazı hatırla" seçilirse cihaza kalıcı tanınma çerezi yazılır.
- **Sadece izin verdiğim cihazlar:** izinsiz cihazların denemeleri listede "İzinsiz" olarak görünür, tek tıkla izin verilir.

### Test
`tests/web_access_test.py`: 24 senaryo (PIN, oturum, kesme, engelleme, onay/ret/hatırla, PIN + onay, izin listesi,
telefondan yasak işlem). Her "telefon" ayrı çerez kavanozu ve tarayıcı kimliğiyle davranır. 24/24 geçti; yayın betiğine eklendi.

---

## 2.6.2 — 27.11.2026 (Odak modu, bütünleşik başlık çubuğu)

- **Odak modu (F11):** sol menü, üst çubuk, görev listesi ve tuş ayarları gizlenir; ekranda sadece cihaz kalır.
  Sağ alttaki yarı saydam "Menüleri göster" butonu ya da F11 ile geri açılır.
- **Düzen menüsü** (üst çubuk): her parça ayrı ayrı gizlenebilir; seçim bu bilgisayarda hatırlanır (localStorage).
  Gizli sol menü fare sol kenara gelince geçici olarak açılır.
- **Başlık çubuğu:** Windows'un çerçevesi korunur (kenara yaslama ve boyutlandırma çalışsın diye); Windows 11'in
  `DWMWA_CAPTION_COLOR` özelliğiyle başlık çubuğu uygulamanın arka plan rengine boyanır, tema değişince güncellenir.
  Doğrulama: gerçek pencerede başlık çubuğu pikseli `#171A21` (uygulama arka planı) okundu.
- Üst çubuk daha saydam (cam görünümü).
- Düzeltilen hata (yayın öncesi): sol menü gizlenince ana içerik 0 genişlikteki ızgara sütununa kayıyordu.

---

## 2.6.1 — 27.11.2026 (Arayüz düzenlemeleri, geliştirici modu)

- Sol üstte "N" yerine NexStudio logosu (96 px'e küçültülüp sayfaya gömülür).
- "Telefon" sekmesi **Web** oldu; metinler telefon, tablet ve başka bilgisayarı kapsayacak şekilde genelleştirildi.
- Tarayıcının hazır `prompt()` / `confirm()` kutuları ("127.0.0.1:xxxx diyor ki") yerine uygulamanın kendi pencereleri.
- Ekran önizlemesinde ◀ ▶ gerçek cihazdaki gibi sayfa değiştirir.
- Yenilikler paneli butona tekrar basınca, dışarı tıklayınca ya da Esc ile kapanır.
- **Geliştirici modu** (Ayarlar > Gelişmiş): kapalıyken üst çubukta sadece "NexDeck bağlı" yazar, port seçimi gizlenir.
  Açıkken COM portu, firmware ve HID bilgisi görünür; sol menüde **Günlük** sekmesi (canlı günlük + hata günlüğü) açılır.
  Canlı günlük için `core.LOG_BUFFER` (son 600 satır) ve `/api2/logs` eklendi.
- Geliştirici araçları: `tools/bump_version.py` (sürüm + uygulama içi yenilikler), `tools/i18n_update.py`,
  `tools/build_lang_plugin.py` + `tools/i18n/de_from_en.json` (Almanca eklentisi artık otomatik üretiliyor).

---

## 2.6.0 — 27.11.2026 (Web modu + dil paketleri)

### Web modu (cihazsız kullanım)
- `config.json > app_mode`: `"device"` (NexDeck ile, varsayılan) ya da `"web"` (cihazsız; telefon sanal NexDeck).
- Web modunda seri porta bağlanılmaz, yeniden bağlanma denenmez, telefondan kontrol otomatik başlar.
  Arayüzde cihaz "Sanal" etiketli görünür; ayarlarda "NexDeck'i kendin yap" rehberi ve **Cihazlı sürüme geç** kartı var.
- Geçiş iki yönde de Ayarlar'dan yapılır, yeniden kurulum gerekmez; tuş atamaları aynen kalır.
- İlk kurulumda (config.json yoksa) karşılama ekranı: dil seçimi + "NexDeck'im var / telefonumla kullanacağım".
- Donanım rehberi: [docs/DONANIM.md](docs/DONANIM.md) (parça listesi, pin bağlantıları, yükleme, sorun giderme).

### Dil paketleri
- Yeni arayüzün metinleri dil paketlerinden gelir. Dil paketi tek bir JSON dosyasıdır:
  `{"name": "English", "ui": {"Türkçe metin": "çeviri", "Profil: {0}": "Profile: {0}"}, "core": {...}}`
  - `ui`: yeni arayüz; anahtar Türkçe metnin kendisidir, `{0}` yer tutucuları desteklenir.
  - `core`: klasik görünüm ve görev adları (locales anahtarları). Boşsa İngilizce'ye düşer.
- Kaynaklar: `src/web_ui/lang/*.json` (uygulamayla gelen), `%APPDATA%\NexStudio\languages\*.json` (kullanıcı), eklentilerdeki `LANGUAGES = {...}`.
- Arayüz, ekrana gelen her metni (yazı, placeholder, title, aria-label) otomatik çevirir; yeni dil için kod değişikliği gerekmez.
- Hazır diller: Türkçe, English (`src/web_ui/lang/en.json`), Deutsch (dil eklentisi örneği: `src/plugins/dil_deutsch.py`).
- Çevirmenler için: `python tools/extract_ui_strings.py <dil.json>` eksik metinleri listeler.
- Klasik görünüm: Türkçe dışındaki dillerde eksik metin artık Türkçe yerine İngilizce'ye düşer.

### Doğrulama
- İlk kurulum (boş veri klasörü): karşılama ekranı açıldı, Almanca seçilince tüm arayüz Almanca'ya döndü,
  "telefonumla kullanacağım" seçilince web modu + telefondan kontrol otomatik başladı, QR hazırdı.
- Görünen metinlerde çevrilmemiş Türkçe kalmadı; 18 duman + 4 canlı olay testi geçti.

---

## 2.5.1 — 27.11.2026 (Modüllere bölme + port düzeltmesi)

### Düzeltilen hata
| Şikayet | Kök neden | Çözüm |
|---|---|---|
| Telefondan kontrol bazen "Yetkisiz" dönüyor / QR ile açılmıyor | Web sunucusu `SO_REUSEADDR` ile açılıyordu. Windows'ta bu, iki programın (ör. kurulu NexStudio + ikinci bir kopya) **aynı portu** dinlemesine izin veriyor. İstek yanlış programa gidiyordu. Boş port arayan fonksiyon da aynı ayar yüzünden dolu portu "boş" sanıyordu. | Port `SO_EXCLUSIVEADDRUSE` ile özel kullanımda; doluysa bir sonraki port seçilir. |

### Kod yapısı
`src/nexstudio_ui.py` (9600 satır) `src/nexstudio/` paketine bölündü. Davranış değişmedi; 18 duman testi, canlı olay ve SendInput testleri bölmeden önce ve sonra aynı sonucu verdi.

| Modül | İçerik |
|---|---|
| `core` | kütüphaneler, dosya yolları, log, görev kuyruğu, SendInput tuş gönderimi, tek kopya |
| `i18n` | dil sistemi |
| `engine` | tuş/sinyal tanımları, hazır görevler, eklentiler, profiller, ayar dosyası, `execute_macro` |
| `webserver` | telefondan kontrol (LAN) sunucusu |
| `serial_link` | Arduino seri haberleşme |
| `app_api` | yeni arayüzün yerel API'si, yerel sunucu, pencere işlemi |
| `classic_widgets` / `classic_app` | klasik görünüm ve ana uygulama sınıfı `NexHubApp` |
| `state` | modüller arasında paylaşılan değerler (`state.APP_CONFIG`, `state.MAIN_WINDOW` …) |

Bölme `tools/split_modules.py` ile yapıldı: modüller arası isimler kod analiziyle (AST) bulunup açık import satırları üretildi.
Bölme sırasında bulunan hata: `app_api.get_state` içindeki yerel `state` değişkeni yeni `state` modülünü gölgeliyordu; adı `result` yapıldı.

---

## 2.5.0 — 27.11.2026 (Yeni arayüz)

### Mimari
- Yeni arayüz `src/web_ui/app.html` (tek dosya, HTML/CSS/JS). Masaüstünde `NexStudio.exe --ui <adres>` ile **ayrı bir pencere işleminde**
  (pywebview + Windows WebView2) açılır. Çekirdek (seri port, görevler, tray) ayrı işlemde çalışmaya devam eder; arayüz çökse bile tuşlar çalışır.
- Çekirdek `127.0.0.1` üzerinde rastgele portta yerel API açar (`AppApi`, `/api2/*`). Her açılışta yeni rastgele anahtar; anahtar
  `runtime.json` dosyasına yazılır, çerez ile taşınır.
- Telefonda aynı HTML **NexStudio Web** olarak açılır (`http://<ip>:<port>/<token>`). Yazma istekleri `X-Nex-Pin` başlığı veya tanınan cihaz
  çerezi ister; ayarlar, cihaz bağlantısı, profil oluşturma/silme sadece bilgisayardan yapılabilir. Eski web arayüzü: adresin sonuna `?classic=1`.
- WebView2 yoksa ya da pencere açılamazsa otomatik olarak klasik (PyQt) görünüm açılır.
- İkinci kez açılınca çalışan kopyaya "göster" sinyali gönderilir (uyarı kutusu yerine pencere öne gelir).

### Yeni özellikler
- Cihaz ortada; görevler sürükle-bırak ya da tıklayarak atanır. Kısa/uzun basış sekmeleri, "Dene", "Görevi kaldır".
- Tuş başına emoji ya da kendi resmi (160 px'e küçültülüp `%APPDATA%\NexStudio\icons` içine kaydedilir).
- Açık/koyu tema, vurgu rengi (hazır + özel), arka plan rengi veya fotoğrafı (2560 px'e küçültülür), panel şeffaflığı.
- Kısayol alanı tuşlara basarak doldurulur (klavye düzeninden bağımsız). Uygulama seçimi için Windows dosya penceresi.
- Telefon sayfası: gerçek QR kod (tıklayınca netleşir), PIN, adres kopyalama, kodu yenileme, tanınan cihazları adlandırma/unutma.
- NexStudio Web'de "Kontrol" modu (tuşa dokun, görev bilgisayarda çalışsın, ses −/+) ve "Düzenle" modu.
- Ekran sayfası adları sekmeye çift tıklayarak değişir; sayfa 3–4 butonlarına ekranda yazacak metin girilebilir.
- Klasik görünüm: Ayarlar > Gelişmiş > "Klasik görünüme geç"; geri dönüş klasik Ayarlar'daki "Yeni görünüme geç" ile.
- Güncelleme Rehberi tüm sürümleri (1.0'dan bugüne) kaydırılabilir şekilde gösterir.
- Tekerlek yeniden döner: sürükleme (her 14° bir adım, eski web arayüzüyle aynı), fare tekerleği, ok tuşları. Adımlar 70 ms'de bir toplu gönderilir.
- Canlı gösterim (`/api2/live`): cihazdaki tuş basışı ekranda yanıp söner, fiziksel tekerlek ekrandaki tekerleği döndürür, ekran butonuna basılınca uygulama o sayfaya geçer.

### Doğrulama
- Yerel API: durum okuma, görev atama, hatalı görev reddi, profil oluşturma/silme, tema, web başlatma (gerçek QR), ses uygulamaları, yetkisiz istek 403.
- Telefon: PIN ile giriş, profil değiştirme izinli; ayar ve profil oluşturma yasak; yanlış PIN 401.
- Paketlenmiş exe yeni pencereyi açtı; kurulumdan sonra cihaz COM12'de firmware 2.0 + HID ile bağlandı.

---

## 2.0.0 — 25.11.2026 (Kararlılık sürümü)

Temel: `NexStudio--NEXT/nexstudio_ui_1_5_final.py` (1.5 Final, 18.06.2026).
Not: 20.06.2026 tarihli kurulu exe aslında **1.5.8 RC** kodundan derlenmişti; Final hiç paketlenmemişti.

### Giderilen hatalar (kök nedenleriyle)

| Şikayet | Kök neden | Çözüm |
|---|---|---|
| Bazı oyunlarda ve OBS'de tuş bazen hiç çalışmıyor | Tuşlar `keybd_event` ile **scan code = 0** ve basılı tutma süresi **0 ms** ile gönderiliyordu. OBS gibi kısayolları periyodik yoklayan programlar ve DirectInput/RawInput kullanan oyunlar bu basışı kaçırıyordu. | `SendInput` + gerçek scan code + 40 ms basılı tutma (`send_key_combo`). Düşük seviye klavye hook'u ile doğrulandı: scan=0x76, ~50 ms. |
| Hile korumalı oyunlarda (ör. Arena Breakout) hiç çalışmıyor | Bu oyunlar yazılımla gönderilen (enjekte edilen) tuşları tamamen yok sayıyor. | **Firmware 2.0 USB HID modu**: NexDeck, tuşu gerçek USB klavye olarak basar. Ayarlar > Tuş Gönderimi ve Uyumluluk > "Otomatik". |
| Yönetici olarak açılan programlarda çalışmıyor | Windows UIPI, normal yetkili programın yönetici pencereye tuş göndermesini engeller. | Hata artık günlükte açıkça yazıyor; Ayarlar'da "Yönetici olarak yeniden başlat" butonu. HID modu bu kısıtlamadan etkilenmez. |
| Kontroller bazen ardarda çalışıyor | Makrolar ve eklentiler **arayüz thread'inde** çalışıyordu. Yavaş bir eklenti (ör. OBS her basışta yeniden bağlanıyordu) arayüzü donduruyor, bu sırada gelen tuşlar kuyrukta birikip donma bitince topluca çalışıyordu. Ayrıca encoder butonu basılı tutulunca her 300 ms'de tekrar gönderiliyordu. | `TaskWorker`: görevler ayrı thread'de sırayla çalışır, 1,5 sn'den eski görevler atlanır. Eklentiler kendi thread'inde çalışır. Aynı sinyal 150 ms içinde tekrar gelirse yok sayılır. Firmware'de encoder butonu kenar algılamalı. |
| Arayüz bozuluyor / rastgele çökme | Web sunucusu thread'leri Qt widget'larına doğrudan dokunuyordu (`log_area.append`, `setStyleSheet`). Qt bunu desteklemez. `QTimer.singleShot` arka thread'den çağrıldığı için hiç çalışmıyordu. | Tüm arka thread erişimleri `ui_log()` ve `run_on_ui()` köprüsünden geçer. Günlük 1500 satırla sınırlı. |
| Arayüzde yazılar kesiliyor | Başlangıç ekranındaki butonlar ve cihaz durum etiketi 1100 px genişliğe sığmıyordu. | Butonlar alt alta, etiketler satır kaydırmalı. |
| Arka planda simge yok | 1.5.8'de tray ikonu düz renk kareydi. | 1.5 Final'deki ikon düzeltmesi artık pakette. |
| Cihaz kopunca uygulama fark etmiyor | `connection_error` sinyali hiçbir yere bağlı değildi. Thread sessizce ölüyor, arayüz "Bağlı" yazmaya devam ediyordu. | Kopma bildirimi (tray), 3 sn'de bir otomatik yeniden bağlanma, firmware 2.0 ile PING/PONG kontrolü. COM numarası değişse bile cihaz seri numarasıyla bulunur. |
| "Bazen hiç çalışmıyor" (açılışta) | Windows ile başlat + elle açma = iki kopya. İkisi aynı COM portunu kapmaya çalışıyordu. | Tek kopya kilidi (named mutex). |
| Ayarların kaybolma riski | `config.json` atomik olmadan, birden fazla thread'den yazılıyordu. Bozuk dosya sessizce varsayılana dönüyordu. | Atomik kayıt + kilit + `config.json.bak` yedeği. Bozuksa yedekten okunur, bozuk dosya `.corrupt-*` olarak saklanır. |
| Dil dosyaları güncellenmiyor | AppData'daki eski `tr.json` uygulamanın yeni metinlerini eziyordu. | Uygulamanın kendi metinleri öncelikli; dosya sadece eksik anahtarları tamamlar. |
| Eklentiler exe'de çalışmıyor / hiç gelmiyor | Paketlenen eklentiler AppData'ya kopyalanmıyordu. `obsws_python` exe'ye eklenmemişti. Eklenti hataları `except: pass` ile yutuluyordu. | `seed_bundled_plugins()`, spec'te hiddenimport, hatalar günlüğe ve `logs/error.log`'a yazılır. |

### Yeni özellikler

- **Profil görevleri:** Herhangi bir cihaz tuşuna "Sonraki profil", "Önceki profil" veya "'X' profiline geç" atanabilir (kategori: 👤 Profil). Her profil kendi tuş atamalarını saklar.
  İpucu: "Sonraki profil" tuşunu her profilde aynı tuşa atayın; aksi halde başka profilde o tuş farklı iş yapar.
- **Cihaz seçimi:** Birden fazla NexDeck listelenir (`Ad · COMx`), Ayarlar'dan adlandırılabilir.
- **Tuş gönderim yöntemi:** Otomatik (cihaz destekliyorsa USB HID) / Sadece yazılım.
- **Eklenti API'si (`nex`):** `nex.send_hotkey("ctrl+s")`, `nex.log()`, `nex.get_setting()` / `nex.set_setting()`. Paketteki 10 eklenti `keyboard.send` yerine bunu kullanacak şekilde güncellendi.
- **OBS eklentisi:** Bağlantıyı tekrar kullanır, kopunca bir kez yeniden bağlanır. Sunucu, şifre ve sahne adları `config.json > plugin_settings > "OBS Studio (API)"` altından ayarlanır.
- **Hata günlüğü:** `%APPDATA%\NexStudio\logs\error.log` (Ayarlar > "Hata günlüğünü aç").
- **Test modu:** `NEXSTUDIO_DATA_DIR` ortam değişkeni ile gerçek ayarlara dokunmadan ayrı klasörde çalışır.

### Kurulum sonrası düzeltmeler (27.11.2026)

- `config.json` artık BOM'lu (Not Defteri ile kaydedilmiş) olsa da okunuyor (`utf-8-sig`). Eskiden okunamayınca varsayılan ayarlara dönüp "Windows ile başlat" kaydını siliyordu.
- "Windows ile başlat" kaydı `KEY_ALL_ACCESS` yerine `KEY_SET_VALUE` ile yazılıyor, exe yolu `sys.executable` ile alınıyor. Hata olursa `error.log`'a yazılıyor.
- Test modu (`NEXSTUDIO_DATA_DIR`) gerçek başlangıç kaydına dokunmuyor.
- Kurulum 64-bit modda: `C:\Program Files\NexStudio`.
- Not (geliştiriciler için): Claude masaüstü uygulaması gibi MSIX paketli bir programın içinden başlatılan işlemler HKCU'ya yazdığında, yazılar paketin sanal kayıt defterine gider. Başlangıç kaydını test ederken uygulamayı Explorer üzerinden başlatın.

### Firmware 2.0 cihaza yüklendi (27.11.2026)

- Yüklemeden önce cihazın flaşı yedeklendi: `hardware/NewArduino/backup/cihaz_onceki_firmware_20261127.hex`.
  Yedek, `NexHubPROTO/dnm/dn/dn.ino` (= `NexDeck_GitHub/hardware/NewArduino`) derlemesiyle bayt bayt %100 aynı çıktı; pin düzeni 2.0 ile aynı.
- Geri dönmek için: `avrdude -p atmega32u4 -c avr109 -P <bootloader portu> -b 57600 -D -U flash:w:cihaz_onceki_firmware_20261127.hex:i`
- Doğrulama: `HELLO` -> `NEXDECK:READY;FW=2.0;CAP=HID,PING`, `PING` -> `PONG`.
  `HID:115` gönderince Windows'a F24 tuşu **enjekte bayrağı olmadan** (gerçek klavye) 46 ms basılı geldi.
- HID eklenince cihazın USB kimliği değişti (COM5 -> COM12, seri no `HIDLD`). NexStudio yeni portu otomatik buldu.
  Not: HID-Project tüm cihazlara aynı seri numarasını (`HIDLD`) veriyor; iki NexDeck takılırsa seri numarasıyla ayırt edilemez, port adıyla ayırt edilir.

### Güvenlik

- Yanlış girilen PIN artık günlüğe düz metin yazılmıyor.
- PIN içeren `mobile_url` config'ten kaldırıldı; web giriş geçmişi 100 kayıtla sınırlı.

### Firmware 2.0 (`hardware/NewArduino/NexDeckArduino.ino`)

- PC'den gelen satırlar bloklamadan okunur. Eski `readStringUntil` döngüyü 1 sn'ye kadar durdurabiliyordu.
- `HELLO` komutuna `NEXDECK:READY;FW=2.0;CAP=HID,PING` cevabı, `PING` komutuna `PONG` cevabı.
- `HID:<kod>,<kod>` ile gerçek USB klavye basışı (HID-Project kütüphanesi).
- Encoder butonu kenar algılama + debounce.
- Eski firmware ile uyumlu: uygulama 1.x firmware'de de çalışır, sadece HID/PING özellikleri kapalı olur.

### Bilinen sınırlamalar / yapılacaklar

- Web arayüzünün API'si hâlâ GET + URL'de PIN kullanıyor (ön yüz değişikliği gerektiriyor).
- Medya tuşları (oynat/duraklat, ses) HID modunda değil yazılımla gönderilir.
- Kod hâlâ tek dosya (~8000 satır); modüllere bölünmesi ve git'e alınması planlanıyor.

# NexStudio Değişiklik Günlüğü

Bu dosya, NexStudio masaüstü uygulamasında ve NexDeck firmware'inde yapılan değişiklikleri kaydeder.
Uygulama içindeki "Güncelleme Rehberi" kartı da aynı bilgiyi kısaca gösterir (`NEXSTUDIO_CHANGELOG`, `src/nexstudio_ui.py`).

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

# NexDeck'i kendin yap

NexDeck; dokunmatik ekranlı, 5 mekanik tuşlu, tekerlekli bir makro kontrol panelidir. Devre, kasa ve yazılım açık kaynak.
Cihazın yoksa NexStudio'yu **Web modunda** kullanabilirsin (telefonun sanal NexDeck olur). Cihazı yapınca Ayarlar > Cihaz > **Cihazlı sürüme geç** demen yeterli; tuş atamaların aynen kalır.

## Parça listesi

| Parça | Adet | Not |
|---|---|---|
| Arduino Pro Micro (ATmega32U4, 5V/16 MHz) | 1 | USB HID desteği için 32U4 şart (Arduino Micro / Leonardo da olur) |
| Nextion 3.5" dokunmatik ekran (NX4832T035) | 1 | Ekran tasarımı: `hardware/Nextion/dsplay.HMI`, yüklenecek dosya: `dsplay.tft` |
| Mekanik tuş (MX uyumlu) + tuş başlığı | 5 | |
| KY-040 döner enkoder (butonlu) | 1 | |
| 12 mm pasif buzzer | 1 | |
| Kablo, lehim, 3D baskı kasa | – | |

2026 fiyatlarıyla toplam maliyet yaklaşık **3.000 TL** (en pahalı parça ekran); benzer ticari ürünlerin yaklaşık yarısı.

## Bağlantılar (firmware 2.0)

| Bileşen | Pro Micro pini | Not |
|---|---|---|
| Tuş 1–5 | D2, D3, D4, D5, D6 | Tuşun diğer ucu GND (dahili pull-up kullanılır) |
| Enkoder A / B | D15, D16 | |
| Enkoder butonu | D9 | Diğer ucu GND |
| Buzzer | D8 | Diğer ucu GND |
| Nextion TX | RX1 (D0) | 9600 baud |
| Nextion RX | TX0 (D1) | |
| Nextion 5V / GND | VCC / GND | Ekran ~250 mA çeker; USB yeterli |

Pinler `hardware/NewArduino/NexDeckArduino.ino` dosyasının başında tanımlı; farklı pin kullanacaksan oradan değiştir.

## Yazılımı yükleme

1. **Firmware:** Arduino IDE'de *Encoder* (Paul Stoffregen) ve *HID-Project* (NicoHood) kütüphanelerini kur. Kart: **Arduino Leonardo**. `hardware/NewArduino/NexDeckArduino.ino` dosyasını yükle.
2. **Ekran:** `hardware/Nextion/dsplay.tft` dosyasını microSD karta kopyala, kartı ekrana takıp ekranı çalıştır (ya da Nextion Editor ile USB-TTL üzerinden yükle).
3. **NexStudio:** [Releases](https://github.com/4llyW3rt/NexDeck/releases) sayfasından kur. Cihazı takınca Sistem Günlüğü'nde `NexDeck tanındı · firmware 2.0 · özellikler: HID, PING` görünür.

## Sorun giderme

- **Cihaz bulunamadı:** Kablo veri kablosu mu (sadece şarj kablosu olmasın)? Aygıt Yöneticisi'nde "Bağlantı noktaları"nda görünüyor mu?
- **Port kullanımda:** Arduino IDE'nin Seri Monitörü açıksa kapat.
- **Tuş oyunda çalışmıyor:** Ayarlar > Gelişmiş > Tuş gönderim yöntemi **Otomatik** olmalı (firmware 2.0 tuşu gerçek USB klavye gibi basar).

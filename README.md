# 🚀 NexDeck - Hibrit Kontrol Paneli #

# ŞUANDA PROTOTİP HALİNDEDİR...
![NexDeck Ana Görsel](main.jpg)
NexDeck, içerik üreticileri ve profesyoneller için geliştirilmiş, yüksek maliyetli kontrol panellerine (Stream Deck vb.) yerli ve ekonomik bir alternatiftir.

### ✨ Öne Çıkan Özellikler
* **Hibrit Kontrol:** Nextion dokunmatik ekran + Fiziksel butonlar + Potansiyometre (Ses ayarı).
* **Maliyet Avantajı:** Piyasadaki muadillerinden %80 daha uygun maliyet.
* **Tam Özelleştirme:** AutoHotkey entegrasyonu ile sınırsız makro desteği.
* **Mekatronik Tasarım:** 3D yazıcı ile üretilen modüler gövde.

### 🛠️ Donanım Bileşenleri
* Arduino Micro (ATmega32U4)
* Nextion HMI Dokunmatik Ekran
* 10K Potansiyometre & Mekanik Butonlar

### 💻 Kurulum
1. `Firmware` klasöründeki kodu Arduino'ya yükleyin.
2. `Nextion` klasöründeki arayüzü ekrana flaşlayın.
3. `Software` klasöründeki AHK scriptini çalıştırın.

### 📝 Proje Hakkında (Project Description)

**NexDeck**, dijital içerik üreticileri, yayıncılar ve profesyonellerin iş akışını optimize etmek amacıyla geliştirilmiş yerli ve ekonomik bir kontrol arayüzüdür. Piyasada bulunan yüksek maliyetli ve kapalı devre sistemlerin aksine NexDeck; hem dokunmatik ekranın esnekliğini hem de fiziksel potansiyometre ve butonların dokunsal hassasiyetini tek bir mekatronik gövdede birleştirir.

### 🎯 Neden NexDeck?
* **Maliyet Etkinliği:** Mevcut profesyonel çözümlere kıyasla %80 daha düşük maliyetle üretilebilir.
* **Hibrit Kontrol:** Nextion HMI ekran üzerinden sınırsız dijital sayfa tasarımı ve fiziksel potansiyometre ile hassas analog ses kontrolü.
* **Açık Kaynak & Özgürlük:** AutoHotkey entegrasyonu sayesinde kullanıcıya özel sınırsız makro ve kısayol atama imkanı.
* **Modüler Yapı:** 3D yazıcı ile üretilen, geliştirilmeye açık ve kişiselleştirilebilir donanım tasarımı.

### 🛠️ Teknik Detaylar
NexDeck; **Arduino Micro** (ATmega32U4) mimarisi üzerine kurulu olup, bilgisayar ile sürücüsüz (Plug & Play) haberleşen bir **HID (Human Interface Device)** aygıtıdır. Seri haberleşme protokolleri ve düşük gecikmeli yazılım yapısıyla profesyonel düzeyde tepki süresi sunar.

### 📝 Sürüm Notları 
v1.1 - Donanım Entegrasyonu ve Akıllı Kısayol Güncellemesi

    🛠️ Fiziksel Butonlar Aktif Edildi: 5 adet push buton donanıma tanıtıldı. Spotify/Medya kontrolleri (Önceki, Oynat/Durdur, Sonraki), sistem geneli mikrofon susturma (F13) ve tek tuşla anında masaüstüne dönme (Panik/Gizlilik - Win+D) işlevleri eklendi.

    🎛️ Rotary Encoder Entegrasyonu: Windows sistem sesini hassas şekilde açma/kısma ve tekerleğe basarak anında sessize alma (Mute) özelliği koda gömüldü.

    🔊 İşitsel Geri Bildirim: Sistemin açılışına ve buton basımlarına pasif buzzer ile dinamik onay sesleri eklendi.

    🖥️ Çekirdek Optimizasyonu: Nextion dokunmatik ekranın mevcut özellikleri (OBS sahne geçişleri, yayın ve kayıt kronometreleri) yeni fiziksel donanımlarla tam senkronize ve çakışmasız çalışacak şekilde aynı loop içinde birleştirildi.

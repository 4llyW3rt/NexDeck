/*
 * =======================================================================================
 * PROJE ADI: NexDeck (Kapsamlı Kontrol Paneli)
 * GELİŞTİRİCİ: Ali Mert - Mekatronik Teknikeri Öğrencisi
 * * * KULLANILAN DONANIMLAR:
 * - Arduino Micro (ATmega32U4 - HID Desteği için)
 * - 3.5" Nextion HMI Dokunmatik Ekran
 * - KY-040 Rotary Encoder (Ses Kontrolü)
 * - 5x Push Buton (Kısayollar ve Acil Durum)
 * - 12mm Pasif Buzzer (Geri Bildirim)
 * * * GEREKLİ KÜTÜPHANELER:
 * 1. HID-Project (NicoHood) -> Gelişmiş medya/klavye tuşları
 * 2. Encoder (Paul Stoffregen) -> Hassas rotary okuması
 * * * PROJE AÇIKLAMASI:
 * NexDeck, karmaşık bilgisayar işlemlerini tek dokunuşa indirgeyen akıllı bir 
 * kontrol panelidir. Sadece yayıncılar için değil; mühendisler, tasarımcılar 
 * ve bilgisayar başında vakit geçiren herkesin günlük hayatında kullanabileceği 
 * pratik bir masaüstü asistanı olarak tasarlanmıştır. Medya kontrolünden, 
 * sistem yönetimine kadar her işi hızlandırır.
 * =======================================================================================
 */

#include <HID-Project.h> 
#include <Encoder.h>

// =========================================================
// 1. DONANIM PİN TANIMLARI
// =========================================================
const int buzzerPin = 2; // Geri bildirim sesleri için pasif buzzer
// Fiziksel Butonlar: S1(D3), S2(D4), S3(D5), S4(D6), S5-Panik(D7)
const int butonlar[] = {3, 4, 5, 6, 7}; 

// Encoder Pinleri
Encoder sesKontrol(9, 10);              
const int encoderButon = 8; // Encoder Butonu (Mute)

long eskiPos = -999; 

// =========================================================
// 2. EKRAN ZAMANLAYICI DEĞİŞKENLERİ
// =========================================================
bool yayinAcik = false; 
unsigned long yayinBaslangicZamani = 0; 
unsigned long sonYayinGuncelleme = 0; 

bool kayitAcik = false; 
unsigned long kayitBaslangicZamani = 0; 
unsigned long sonKayitGuncelleme = 0; 

// =========================================================
// 3. YARDIMCI FONKSİYONLAR
// =========================================================
void ekranaYaz(String objeAdi, String metin) { 
  Serial1.print(objeAdi + ".txt=\"" + metin + "\""); 
  Serial1.write(0xFF); Serial1.write(0xFF); Serial1.write(0xFF); 
} 

void setup() { 
  Serial1.begin(9600); 
  Keyboard.begin();    
  Consumer.begin();    
  
  pinMode(buzzerPin, OUTPUT);
  pinMode(encoderButon, INPUT_PULLUP); 
  for(int i=0; i<5; i++) {
    pinMode(butonlar[i], INPUT_PULLUP);
  }

  // NexDeck Sistem Hazır Sinyali
  tone(buzzerPin, 1000, 100); delay(100); tone(buzzerPin, 1500, 150);
} 

void loop() { 
  unsigned long suAnkiZaman = millis(); 

  // =========================================================
  // BÖLÜM A: ZAMANLAYICILAR VE EKRAN GÜNCELLEMELERİ
  // =========================================================
  if (yayinAcik && (suAnkiZaman - sonYayinGuncelleme >= 1000)) { 
    sonYayinGuncelleme = suAnkiZaman; 
    unsigned long gecenSaniye = (suAnkiZaman - yayinBaslangicZamani) / 1000; 
    int s = gecenSaniye % 60; int m = (gecenSaniye / 60) % 60; int h = gecenSaniye / 3600; 
    char zamanMetni[10]; sprintf(zamanMetni, "%02d:%02d:%02d", h, m, s); 
    ekranaYaz("page0.t0", zamanMetni);  
  } 

  if (kayitAcik && (suAnkiZaman - sonKayitGuncelleme >= 1000)) { 
    sonKayitGuncelleme = suAnkiZaman;  
    unsigned long gecenSaniye = (suAnkiZaman - kayitBaslangicZamani) / 1000; 
    int s = gecenSaniye % 60; int m = (gecenSaniye / 60) % 60; int h = gecenSaniye / 3600; 
    char zamanMetni[10]; sprintf(zamanMetni, "%02d:%02d:%02d", h, m, s); 
    ekranaYaz("page1.t0", zamanMetni); 
  } 

  // =========================================================
  // BÖLÜM B: NEXTION DOKUNMATİK EKRAN KOMUTLARI
  // =========================================================
  if (Serial1.available()) { 
    String gelenMesaj = Serial1.readStringUntil('\0'); 

    if (gelenMesaj == "MIC_TOGGLE") { Keyboard.write(KEY_F13); } 
    else if (gelenMesaj == "CAM_TOGGLE") { Keyboard.write(KEY_F14); } 
    else if (gelenMesaj == "DESK_TOGGLE") { Keyboard.write(KEY_F15); } 
    
    else if (gelenMesaj == "LIVE_TOGGLE") {  
      Keyboard.write(KEY_F16);  
      yayinAcik = !yayinAcik; 
      if (yayinAcik) { yayinBaslangicZamani = millis(); } 
      else { ekranaYaz("page0.t0", "00:00:00"); } 
    }  
    
    else if (gelenMesaj == "SCENE_1") { Keyboard.write(KEY_F17); } 
    else if (gelenMesaj == "SCENE_2") { Keyboard.write(KEY_F18); } 
    else if (gelenMesaj == "SCENE_3") { Keyboard.write(KEY_F19); } 

    else if (gelenMesaj == "REC_TOGGLE") {  
      Keyboard.write(KEY_F20);  
      kayitAcik = !kayitAcik; 
      if (kayitAcik) { kayitBaslangicZamani = millis(); } 
      else { ekranaYaz("page1.t0", "00:00:00"); } 
    }  
    else if (gelenMesaj == "OPEN_YT") { Keyboard.write(KEY_F21); } 
    else if (gelenMesaj == "OPEN_KICK") { Keyboard.write(KEY_F22); } 

    else if (gelenMesaj == "MEDIA_PREV") { Consumer.write(MEDIA_PREVIOUS); } 
    else if (gelenMesaj == "MEDIA_PP") { Consumer.write(MEDIA_PLAY_PAUSE); } 
    else if (gelenMesaj == "MEDIA_NEXT") { Consumer.write(MEDIA_NEXT); } 
  } 

  // =========================================================
  // BÖLÜM C: FİZİKSEL ENCODER (SES KONTROLÜ)
  // =========================================================
  long yeniPos = sesKontrol.read() / 4; 
  if (yeniPos != eskiPos) {
    if (yeniPos > eskiPos) Consumer.write(MEDIA_VOLUME_UP);   
    else Consumer.write(MEDIA_VOLUME_DOWN);                   
    eskiPos = yeniPos;
  }
  
  if (digitalRead(encoderButon) == LOW) {
    Consumer.write(MEDIA_VOL_MUTE);
    tone(buzzerPin, 800, 100);
    delay(400); 
  }

  // =========================================================
  // BÖLÜM D: FİZİKSEL BUTONLAR
  // =========================================================
  // S1 (D3): Mikrofonu Sustur (F13)
  if (digitalRead(butonlar[0]) == LOW) { Keyboard.write(KEY_F13); tone(buzzerPin, 1200, 100); delay(300); }
  
  // S2 (D4): Spotify Önceki Şarkı
  if (digitalRead(butonlar[1]) == LOW) { Consumer.write(MEDIA_PREVIOUS); tone(buzzerPin, 900, 50); delay(300); }
  
  // S3 (D5): Spotify Oynat/Durdur
  if (digitalRead(butonlar[2]) == LOW) { Consumer.write(MEDIA_PLAY_PAUSE); tone(buzzerPin, 1000, 50); delay(300); }
  
  // S4 (D6): Spotify Sonraki Şarkı
  if (digitalRead(butonlar[3]) == LOW) { Consumer.write(MEDIA_NEXT); tone(buzzerPin, 1100, 50); delay(300); }
  
  // S5 (D7): PANİK BUTONU (Temiz Masaüstü - Win+D)
  if (digitalRead(butonlar[4]) == LOW) {
    tone(buzzerPin, 800, 100); 
    Keyboard.press(KEY_LEFT_GUI); 
    Keyboard.press('d');          
    delay(100); 
    Keyboard.releaseAll();        
    delay(1000); 
  }
}

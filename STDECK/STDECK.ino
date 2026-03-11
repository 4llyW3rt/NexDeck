#include <HID-Project.h>

const int PANIK_BUTONU = 2; // Fiziksel panik (PC kapatma) butonu pini

// --- ZAMANLAYICI (TIMER) DEĞİŞKENLERİ ---
bool yayinAcik = false;
unsigned long yayinBaslangicZamani = 0;
unsigned long sonYayinGuncelleme = 0;

bool kayitAcik = false;
unsigned long kayitBaslangicZamani = 0;
unsigned long sonKayitGuncelleme = 0;

void setup() {
  Serial1.begin(9600);
  Keyboard.begin();
  Consumer.begin();
  pinMode(PANIK_BUTONU, INPUT_PULLUP);
}

// Nextion ekrandaki yazıları anında değiştirmeye yarayan sihirli fonksiyonumuz
void ekranaYaz(String objeAdi, String metin) {
  Serial1.print(objeAdi + ".txt=\"" + metin + "\"");
  Serial1.write(0xFF);
  Serial1.write(0xFF);
  Serial1.write(0xFF);
}

void loop() {
  // ---------------------------------------------------------
  // 1. ZAMANLAYICILARIN ÇALIŞTIRILMASI (Arka Plan Zekası)
  // ---------------------------------------------------------
  unsigned long suAnkiZaman = millis();

  // --- YAYIN SÜRESİ (1. Sayfa) ---
  if (yayinAcik && (suAnkiZaman - sonYayinGuncelleme >= 1000)) {
    sonYayinGuncelleme = suAnkiZaman; // 1 saniye geçtiğini kaydet
    
    // Geçen süreyi Saat:Dakika:Saniye formatına çevir
    unsigned long gecenSaniye = (suAnkiZaman - yayinBaslangicZamani) / 1000;
    int s = gecenSaniye % 60;
    int m = (gecenSaniye / 60) % 60;
    int h = gecenSaniye / 3600;
    
    char zamanMetni[10];
    sprintf(zamanMetni, "%02d:%02d:%02d", h, m, s); // 00:00:00 şekline getir
    
    // 1. sayfadaki (page0) t0 isimli metin kutusuna süreyi yolla
    ekranaYaz("page0.t0", zamanMetni); 
  }

  // --- KAYIT SÜRESİ (2. Sayfa) ---
  if (kayitAcik && (suAnkiZaman - sonKayitGuncelleme >= 1000)) {
    sonKayitGuncelleme = suAnkiZaman; 
    
    unsigned long gecenSaniye = (suAnkiZaman - kayitBaslangicZamani) / 1000;
    int s = gecenSaniye % 60;
    int m = (gecenSaniye / 60) % 60;
    int h = gecenSaniye / 3600;
    
    char zamanMetni[10];
    sprintf(zamanMetni, "%02d:%02d:%02d", h, m, s);
    
    // 2. sayfadaki (page1) t0 isimli metin kutusuna süreyi yolla
    ekranaYaz("page1.t0", zamanMetni);
  }

  // ---------------------------------------------------------
  // 2. NEXTION EKRANDAN GELEN KOMUTLARI DİNLEME
  // ---------------------------------------------------------
  if (Serial1.available()) {
    String gelenMesaj = Serial1.readStringUntil('\0');

    // --- 1. SAYFA KONTROLLERİ ---
    if (gelenMesaj == "MIC_TOGGLE") { Keyboard.write(KEY_F13); }
    else if (gelenMesaj == "CAM_TOGGLE") { Keyboard.write(KEY_F14); }
    else if (gelenMesaj == "DESK_TOGGLE") { Keyboard.write(KEY_F15); }
    
    // Canlı Yayın Tuşu (Zamanlayıcıyı Başlat/Durdur)
    else if (gelenMesaj == "LIVE_TOGGLE") { 
      Keyboard.write(KEY_F16); 
      yayinAcik = !yayinAcik; // Durumu tersine çevir
      if (yayinAcik) {
        yayinBaslangicZamani = millis(); // Kronometreyi başlat
      } else {
        ekranaYaz("page0.t0", "00:00:00"); // Kapanınca ekranı sıfırla
      }
    } 
    
    // --- 1. SAYFA SAHNE GEÇİŞLERİ ---
    else if (gelenMesaj == "SCENE_1") { Keyboard.write(KEY_F17); }
    else if (gelenMesaj == "SCENE_2") { Keyboard.write(KEY_F18); }
    else if (gelenMesaj == "SCENE_3") { Keyboard.write(KEY_F19); }

    // --- 2. SAYFA OBS, YOUTUBE VE KICK ---
    // Kayıt Tuşu (Zamanlayıcıyı Başlat/Durdur)
    else if (gelenMesaj == "REC_TOGGLE") { 
      Keyboard.write(KEY_F20); 
      kayitAcik = !kayitAcik;
      if (kayitAcik) {
        kayitBaslangicZamani = millis();
      } else {
        ekranaYaz("page1.t0", "00:00:00");
      }
    } 
    else if (gelenMesaj == "OPEN_YT") { Keyboard.write(KEY_F21); }
    else if (gelenMesaj == "OPEN_KICK") { Keyboard.write(KEY_F22); }

    // --- MEDYA KONTROLLERİ (Ortak) ---
    else if (gelenMesaj == "MEDIA_PREV") { Consumer.write(MEDIA_PREVIOUS); }
    else if (gelenMesaj == "MEDIA_PP") { Consumer.write(MEDIA_PLAY_PAUSE); }
    else if (gelenMesaj == "MEDIA_NEXT") { Consumer.write(MEDIA_NEXT); }
  }

  // ---------------------------------------------------------
  // 3. FİZİKSEL PANİK BUTONUNU DİNLEME
  // ---------------------------------------------------------
  if (digitalRead(PANIK_BUTONU) == LOW) {
    delay(50);
    if (digitalRead(PANIK_BUTONU) == LOW) {
      Keyboard.press(KEY_LEFT_GUI);
      Keyboard.press('r');
      delay(100);
      Keyboard.releaseAll();
      delay(300); 
      Keyboard.print("shutdown /s /f /t 0");
      delay(100);
      Keyboard.write(KEY_RETURN);
      delay(10000); 
    }
  }
}
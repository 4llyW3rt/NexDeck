/*
 * =======================================================================================
 * NexDeck Firmware 2.0  (Arduino Pro Micro / ATmega32U4)
 * Geliştirici: Ali Mert Taşcı / NexHub
 *
 * PC <-> NexDeck seri protokolü (9600 baud, satır sonu '\n'):
 *   Cihazdan PC'ye:
 *     NEXDECK:READY;FW=2.0;CAP=HID,PING   açılışta ve HELLO'ya cevap olarak
 *     BTN:n  /  BTN:n:LONG                 fiziksel tuşlar (n = 1..5)
 *     ENC:UP / ENC:DOWN / ENC:BTN          tekerlek
 *     NEX:<metin>                          Nextion dokunmatik ekrandan gelen komut
 *     PONG                                 PING cevabı (bağlantı kontrolü)
 *     HID_OK / HID_ERR                     HID tuş gönderim sonucu
 *     DEBUG_NEX_SENT:<komut>               ekrana iletilen komut (günlük için)
 *   PC'den cihaza:
 *     HELLO                                kimlik iste
 *     PING                                 bağlantı kontrolü
 *     NEXCMD:<komut>                       Nextion ekrana komut ilet
 *     HID:<kod>,<kod>,...                  USB HID kullanım kodlarını gerçek klavye gibi bas
 *                                          (0xE0-0xE7 = Ctrl/Shift/Alt/Win modifier'ları)
 *
 * Gerekli kütüphaneler: Encoder (Paul Stoffregen), HID-Project (NicoHood)
 *
 * 1.x'e göre değişiklikler:
 *   - Seri okuma bloklamıyor (readStringUntil 1 sn'ye kadar döngüyü durdurabiliyordu;
 *     bu sırada tuş/tekerlek olayları kaçıyordu).
 *   - Tekerlek butonu artık kenar algılamalı: basılı tutunca tekrar tekrar tetiklenmiyor.
 *   - USB HID klavye modu: hile korumalı oyunlar yazılımsal tuşları yok sayar,
 *     NexDeck tuşu gerçek klavye olarak bastığı için çalışır.
 *   - PING/PONG ve kimlik satırı: uygulama kopmayı algılar, firmware sürümünü bilir.
 * =======================================================================================
 */

#include <Encoder.h>
#include <HID-Project.h>   // NicoHood HID-Project: ham USB HID tuş kodlarını doğrudan basar

#define FW_VERSION "2.0"

// ── DONANIM PİNLERİ (PRO MICRO) ──
const int buzzerPin    = 8;
const int butonlar[]   = {2, 3, 4, 5, 6};
Encoder sesKontrol(15, 16);
const int encoderButon = 9;

// ── ZAMANLAMA ──
const unsigned long LONG_PRESS_TIME = 600;
const unsigned long DEBOUNCE_TIME   = 50;
const unsigned long HID_HOLD_TIME   = 40;   // Tuşun basılı kalma süresi (oyunlar kısa basışı kaçırmasın)

// ── DURUM ──
long eskiPos = -999;
int  lastButtonState[5]          = {HIGH, HIGH, HIGH, HIGH, HIGH};
unsigned long buttonPressTime[5] = {0};
bool longPressTriggered[5]       = {false};

int  encBtnStableState      = HIGH;
int  encBtnLastReading      = HIGH;
unsigned long encBtnChanged = 0;

String pcBuffer = "";
String nextionBuffer = "";
unsigned long lastNextionCharTime = 0;

// PC bağlı değilken USB seriye yazmak döngüyü yavaşlatmasın.
void sendLine(const String &line) {
  if (Serial) Serial.println(line);
}

void sendHello() {
  sendLine(String("NEXDECK:READY;FW=") + FW_VERSION + ";CAP=HID,PING");
}

// Geçerli USB HID klavye kullanım kodu mu? (0x04-0x73 normal tuşlar, 0xE0-0xE7 modifier)
bool isValidUsage(int usage) {
  return (usage >= 0x04 && usage <= 0x73) || (usage >= 0xE0 && usage <= 0xE7);
}

void handleHidCommand(const String &payload) {
  uint8_t keys[6];
  int count = 0;
  int start = 0;
  while (start < (int)payload.length() && count < 6) {
    int comma = payload.indexOf(',', start);
    if (comma < 0) comma = payload.length();
    int usage = payload.substring(start, comma).toInt();
    if (!isValidUsage(usage)) { sendLine("HID_ERR:" + payload); return; }
    keys[count++] = (uint8_t)usage;
    start = comma + 1;
  }
  if (count == 0) { sendLine("HID_ERR:bos"); return; }
  for (int i = 0; i < count; i++) { Keyboard.press((KeyboardKeycode)keys[i]); delay(5); }
  delay(HID_HOLD_TIME);
  Keyboard.releaseAll();
  sendLine("HID_OK");
}

void handlePcLine(String line) {
  line.trim();
  if (line.length() == 0) return;
  if (line == "HELLO") { sendHello(); }
  else if (line == "PING") { sendLine("PONG"); }
  else if (line.startsWith("HID:")) { handleHidCommand(line.substring(4)); }
  else if (line.startsWith("NEXCMD:")) {
    String nexCmd = line.substring(7);
    Serial1.print(nexCmd);
    Serial1.write(0xFF); Serial1.write(0xFF); Serial1.write(0xFF);
    sendLine("DEBUG_NEX_SENT:" + nexCmd);
  }
}

void setup() {
  Serial.begin(9600);    // PC (USB)
  Serial1.begin(9600);   // Nextion ekran (UART)
  Keyboard.begin();

  pinMode(buzzerPin, OUTPUT);
  pinMode(encoderButon, INPUT_PULLUP);
  for (int i = 0; i < 5; i++) pinMode(butonlar[i], INPUT_PULLUP);

  pcBuffer.reserve(96);
  nextionBuffer.reserve(48);

  tone(buzzerPin, 500, 100); delay(150);
  tone(buzzerPin, 700, 100);
  sendHello();
}

void loop() {
  unsigned long simdi = millis();

  // ── 1. PC'DEN GELEN KOMUTLAR (bloklamadan, karakter karakter) ──
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') { handlePcLine(pcBuffer); pcBuffer = ""; }
    else if (c != '\r') {
      if (pcBuffer.length() < 90) pcBuffer += c;
      else pcBuffer = "";  // taşma: bozuk satırı at
    }
  }

  // ── 2. EKRANDAN GELEN KOMUTLARI PC'YE AKTAR ──
  while (Serial1.available()) {
    char c = Serial1.read();
    lastNextionCharTime = simdi;
    if (c == '\0' || c == '\n' || c == '\r') {
      nextionBuffer.trim();
      if (nextionBuffer.length() > 0) sendLine("NEX:" + nextionBuffer);
      nextionBuffer = "";
    } else if (c >= 32 && c <= 126 && nextionBuffer.length() < 40) {
      nextionBuffer += c;
    }
  }
  if (nextionBuffer.length() > 0 && (simdi - lastNextionCharTime > 30)) {
    nextionBuffer.trim();
    if (nextionBuffer.length() > 0) sendLine("NEX:" + nextionBuffer);
    nextionBuffer = "";
  }

  // ── 3. TEKERLEK ──
  long yeniPos = sesKontrol.read() / 4;
  if (yeniPos != eskiPos) {
    if (eskiPos != -999) sendLine(yeniPos > eskiPos ? "ENC:UP" : "ENC:DOWN");
    eskiPos = yeniPos;
  }

  // Tekerlek butonu: sadece basıldığı anda bir kez (kenar algılama + debounce)
  int encReading = digitalRead(encoderButon);
  if (encReading != encBtnLastReading) { encBtnChanged = simdi; encBtnLastReading = encReading; }
  if ((simdi - encBtnChanged) > DEBOUNCE_TIME && encReading != encBtnStableState) {
    encBtnStableState = encReading;
    if (encBtnStableState == LOW) {
      tone(buzzerPin, 500, 80);
      sendLine("ENC:BTN");
    }
  }

  // ── 4. FİZİKSEL BUTONLAR (kısa / uzun basış) ──
  for (int i = 0; i < 5; i++) {
    int currentState = digitalRead(butonlar[i]);

    if (currentState == LOW && lastButtonState[i] == HIGH) {
      if (simdi - buttonPressTime[i] > DEBOUNCE_TIME) {
        buttonPressTime[i] = simdi;
        longPressTriggered[i] = false;
        lastButtonState[i] = LOW;
      }
    }
    else if (currentState == LOW && lastButtonState[i] == LOW) {
      if (!longPressTriggered[i] && (simdi - buttonPressTime[i] > LONG_PRESS_TIME)) {
        longPressTriggered[i] = true;
        tone(buzzerPin, 800, 150);
        sendLine("BTN:" + String(i + 1) + ":LONG");
      }
    }
    else if (currentState == HIGH && lastButtonState[i] == LOW) {
      if (simdi - buttonPressTime[i] > DEBOUNCE_TIME) {
        if (!longPressTriggered[i]) {
          tone(buzzerPin, 500, 100);
          sendLine("BTN:" + String(i + 1));
        }
        lastButtonState[i] = HIGH;
        buttonPressTime[i] = simdi;
      }
    }
  }
}

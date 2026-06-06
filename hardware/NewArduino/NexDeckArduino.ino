#include <Encoder.h>

// DONANIM PINLERİ (PRO MICRO)
const int buzzerPin    = 8;
const int butonlar[]   = {2, 3, 4, 5, 6};
Encoder sesKontrol(15, 16);
const int encoderButon = 9;

long eskiPos = -999;
int lastButtonState[5] = {HIGH, HIGH, HIGH, HIGH, HIGH};
unsigned long buttonPressTime[5] = {0};
bool longPressTriggered[5] = {false};
const unsigned long LONG_PRESS_TIME = 600;
const unsigned long DEBOUNCE_TIME = 50; 

unsigned long sonEncoderBasim = 0;
const unsigned long ENCODER_DEBOUNCE = 300;

String nextionBuffer = "";
unsigned long lastNextionCharTime = 0;

void setup() {
  Serial.begin(9600);    // PC ile iletişim (USB)
  Serial1.begin(9600);   // Ekran ile iletişim (UART)

  pinMode(buzzerPin, OUTPUT);
  pinMode(encoderButon, INPUT_PULLUP);
  for (int i = 0; i < 5; i++) pinMode(butonlar[i], INPUT_PULLUP);

  tone(buzzerPin, 500, 100); delay(150);
  tone(buzzerPin, 500, 100);
  Serial.println("NEXDECK:READY");
}

void loop() {
  unsigned long suAnkiZaman = millis();

  // ── 1. PC'DEN GELEN KOMUTLARI EKRANA AKTAR (DÜZELTİLDİ) ──
  if (Serial.available()) {
    String pcCmd = Serial.readStringUntil('\n');
    pcCmd.trim();
    if (pcCmd.startsWith("NEXCMD:")) {
      String nexCmd = pcCmd.substring(7); // NEXCMD: kısmını sil!
      Serial1.print(nexCmd); 
      Serial1.write(0xFF); Serial1.write(0xFF); Serial1.write(0xFF);
      Serial.println("DEBUG_NEX_SENT:" + nexCmd); // Log ekranında görmek için
    }
  }

  // ── 2. EKRANDAN GELEN KOMUTLARI PC'YE AKTAR ──
  while (Serial1.available()) {
    char c = Serial1.read();
    lastNextionCharTime = millis();
    
    if (c == '\0' || c == '\n' || c == '\r') {
      nextionBuffer.trim();
      if (nextionBuffer.length() > 0) {
        Serial.println("NEX:" + nextionBuffer);
      }
      nextionBuffer = "";
    } else {
      if (c >= 32 && c <= 126) {
        nextionBuffer += c;
      }
    }
  }

  if (nextionBuffer.length() > 0 && (millis() - lastNextionCharTime > 30)) {
    nextionBuffer.trim();
    Serial.println("NEX:" + nextionBuffer);
    nextionBuffer = "";
  }

  // ── 3. SES TEKERLEĞİ ──
  long yeniPos = sesKontrol.read() / 4;
  if (yeniPos != eskiPos) {
    if (yeniPos > eskiPos) Serial.println("ENC:UP");
    else                   Serial.println("ENC:DOWN");
    eskiPos = yeniPos;
  }
  if (digitalRead(encoderButon) == LOW) {
    if (suAnkiZaman - sonEncoderBasim > ENCODER_DEBOUNCE) {
      sonEncoderBasim = suAnkiZaman;
      tone(buzzerPin, 500, 100);
      Serial.println("ENC:BTN");
    }
  }

  // ── 4. FİZİKSEL BUTONLAR (HIZLANDIRILDI) ──
  for (int i = 0; i < 5; i++) {
    int currentState = digitalRead(butonlar[i]);
    
    if (currentState == LOW && lastButtonState[i] == HIGH) {
      if (suAnkiZaman - buttonPressTime[i] > DEBOUNCE_TIME) {
        buttonPressTime[i] = suAnkiZaman;
        longPressTriggered[i] = false;
        lastButtonState[i] = LOW;
      }
    }
    else if (currentState == LOW && lastButtonState[i] == LOW) {
      if (!longPressTriggered[i] && (suAnkiZaman - buttonPressTime[i] > LONG_PRESS_TIME)) {
        longPressTriggered[i] = true;
        tone(buzzerPin, 800, 150);
        Serial.println("BTN:" + String(i+1) + ":LONG");
      }
    }
    else if (currentState == HIGH && lastButtonState[i] == LOW) {
      if (suAnkiZaman - buttonPressTime[i] > DEBOUNCE_TIME) {
        if (!longPressTriggered[i]) {
          tone(buzzerPin, 500, 100);
          Serial.println("BTN:" + String(i+1));
        }
        lastButtonState[i] = HIGH;
        buttonPressTime[i] = suAnkiZaman;
      }
    }
  }
}
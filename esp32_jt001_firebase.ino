#include <WiFi.h>
#include <Firebase_ESP_Client.h>

#define WIFI_SSID "CC104-2.4GHz"
#define WIFI_PASSWORD "321@cc104"

#define API_KEY "AIzaSyAMstKG96DUKOPbJQZKKssWtHbc4iLtccI"
#define DATABASE_URL "https://antibullyingsystem-95305-default-rtdb.firebaseio.com/"

#define ROOM_ID "JT001"
#define MIC_PIN 34

#define SAMPLE_WINDOW_MS 500
#define LOOP_DELAY_MS 250
#define ALERT_COOLDOWN_MS 8000

// Adjust these after reading the serial output in the real room.
#define ALERT_PEAK_TO_PEAK 900
#define ALERT_AVG_DEVIATION 180

FirebaseData fbdo;
FirebaseAuth auth;
FirebaseConfig config;

unsigned long lastAlertMs = 0;
bool lastAlertState = false;

void connectWiFi() {
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("Connecting WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.print("WiFi connected. IP: ");
  Serial.println(WiFi.localIP());
}

void connectFirebase() {
  config.api_key = API_KEY;
  config.database_url = DATABASE_URL;

  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);
}

void ensureRoomExists() {
  String base = String("rooms/") + ROOM_ID;

  Firebase.RTDB.setString(&fbdo, base + "/status", "NORMAL");
  Firebase.RTDB.setString(&fbdo, base + "/device", "ESP32-MAX9814");
  Firebase.RTDB.setInt(&fbdo, base + "/sampleWindowMs", SAMPLE_WINDOW_MS);
}

void readSoundMetrics(int &peakToPeak, int &avgDeviation) {
  unsigned long startMs = millis();
  int signalMin = 4095;
  int signalMax = 0;
  long deviationSum = 0;
  int sampleCount = 0;

  while (millis() - startMs < SAMPLE_WINDOW_MS) {
    int raw = analogRead(MIC_PIN);

    if (raw < signalMin) {
      signalMin = raw;
    }
    if (raw > signalMax) {
      signalMax = raw;
    }

    deviationSum += abs(raw - 2048);
    sampleCount++;
    delayMicroseconds(250);
  }

  peakToPeak = signalMax - signalMin;
  avgDeviation = sampleCount > 0 ? deviationSum / sampleCount : 0;
}

void updateFirebaseStatus(bool alertState, int peakToPeak, int avgDeviation) {
  String base = String("rooms/") + ROOM_ID;
  String status = alertState ? "ALERT" : "NORMAL";

  Firebase.RTDB.setString(&fbdo, base + "/status", status);
  Firebase.RTDB.setInt(&fbdo, base + "/peakToPeak", peakToPeak);
  Firebase.RTDB.setInt(&fbdo, base + "/avgDeviation", avgDeviation);
  Firebase.RTDB.setString(&fbdo, base + "/device", "ESP32-MAX9814");
}

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  analogSetPinAttenuation(MIC_PIN, ADC_11db);

  connectWiFi();
  connectFirebase();
  ensureRoomExists();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  int peakToPeak = 0;
  int avgDeviation = 0;
  readSoundMetrics(peakToPeak, avgDeviation);

  bool loudSound = peakToPeak >= ALERT_PEAK_TO_PEAK && avgDeviation >= ALERT_AVG_DEVIATION;
  bool inCooldown = millis() - lastAlertMs < ALERT_COOLDOWN_MS;
  bool alertState = loudSound || inCooldown;

  if (loudSound) {
    lastAlertMs = millis();
  }

  Serial.print("peakToPeak=");
  Serial.print(peakToPeak);
  Serial.print(" avgDeviation=");
  Serial.print(avgDeviation);
  Serial.print(" status=");
  Serial.println(alertState ? "ALERT" : "NORMAL");

  if (alertState != lastAlertState || loudSound) {
    updateFirebaseStatus(alertState, peakToPeak, avgDeviation);
    lastAlertState = alertState;
  }

  delay(LOOP_DELAY_MS);
}

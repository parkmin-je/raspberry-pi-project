#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>
#include <ArduinoJson.h>

#define DHTPIN 4
#define DHTTYPE DHT11

const char* ssid     = "RPI_Hotspot";
const char* password = "12345678";
const char* serverURL = "http://10.42.0.1:5000/api/sensor";

DHT dht(DHTPIN, DHTTYPE);

void setup() {
    Serial.begin(115200);
    dht.begin();
    WiFi.begin(ssid, password);
    Serial.print("WiFi 연결중");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\n✅ WiFi 연결 완료!");
    Serial.print("ESP32 IP: ");
    Serial.println(WiFi.localIP());
}

void loop() {
    float humidity    = dht.readHumidity();
    float temperature = dht.readTemperature();

    if (isnan(humidity) || isnan(temperature)) {
        Serial.println("❌ DHT 센서 읽기 실패!");
        delay(2000);
        return;
    }

    Serial.printf("온도: %.1f°C, 습도: %.1f%%\n", temperature, humidity);

    if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        http.begin(serverURL);
        http.addHeader("Content-Type", "application/json");

        StaticJsonDocument<100> doc;
        doc["temperature"] = temperature;
        doc["humidity"]    = humidity;
        String jsonStr;
        serializeJson(doc, jsonStr);

        int httpCode = http.POST(jsonStr);
        if (httpCode == 200) {
            Serial.println("✅ 서버 전송 성공");
        } else {
            Serial.printf("❌ 전송 실패, 코드: %d\n", httpCode);
        }
        http.end();
    }
    delay(2000);
}

# ESP32 + DHT11 센서 모니터링 시스템

## 구조
```
[ESP32 + DHT11] → HTTP POST → [라즈베리파이 Flask] ← AJAX ← [브라우저]
```

## 구성
- **arduino/** : ESP32 아두이노 코드 (DHT11 온습도 센서)
- **raspberry-pi/** : Flask 웹서버 (데이터 수신 + 그래프 페이지)
- **web/** : 실시간 AJAX 그래프 모니터링 UI

## 실행 방법
```bash
cd raspberry-pi
python3 app.py
```
브라우저에서 `http://라즈베리파이IP:5000` 접속

## 사용 라이브러리
- ESP32: WiFi, HTTPClient, DHT, ArduinoJson
- 라즈베리파이: Flask, collections

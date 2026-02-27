import paho.mqtt.client as mqtt
from flask import Flask, render_template_string
from flask_socketio import SocketIO
from datetime import datetime
from collections import deque
import json
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

history = deque(maxlen=50)
sensor_data = {"temperature": 0, "humidity": 0, "timestamp": ""}

BROKER_HOST = "broker.emqx.io"
BROKER_PORT = 1883
TOPIC       = "python/mqtt"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ MQTT 브로커 연결 완료!")
        client.subscribe(TOPIC, qos=1)
    else:
        print(f"❌ 연결 실패: {rc}")

def on_message(client, userdata, msg):
    global sensor_data
    try:
        payload = json.loads(msg.payload.decode())
        sensor_data = {
            "temperature": payload.get("temperature", 0),
            "humidity":    payload.get("humidity", 0),
            "timestamp":   datetime.now().strftime("%H:%M:%S")
        }
        history.append(dict(sensor_data))
        print(f"[수신] {msg.topic} | {sensor_data}")
        socketio.emit('sensor_update', {
            "current": sensor_data,
            "history": list(history)
        })
    except Exception as e:
        print(f"파싱 오류: {e}")

def start_mqtt():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER_HOST, BROKER_PORT, 60)
    client.loop_forever()

threading.Thread(target=start_mqtt, daemon=True).start()

@socketio.on('connect')
def on_browser_connect():
    print("🌐 브라우저 연결됨")

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/test')
def test_publish():
    import paho.mqtt.publish as publish
    import random
    data = {
        "temperature": round(random.uniform(20, 35), 1),
        "humidity":    round(random.uniform(40, 80), 1)
    }
    publish.single(TOPIC, json.dumps(data), hostname=BROKER_HOST, qos=1)
    return f"발행 완료: {data}"

HTML_PAGE = """
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MQTT 센서 대시보드</title>
<script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Segoe UI', sans-serif; background: #0f0f1a; color: #fff; min-height: 100vh; padding: 30px 20px; }
  h1 { text-align: center; font-size: 1.4rem; font-weight: 400; color: #888; letter-spacing: 4px; text-transform: uppercase; margin-bottom: 6px; }
  .badge { text-align: center; font-size: 0.75rem; color: #f7b731; letter-spacing: 2px; margin-bottom: 25px; }
  .badge span { display: inline-block; width: 8px; height: 8px; background: #f7b731; border-radius: 50%; margin-right: 6px; animation: pulse 1.5s infinite; }
  @keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.4;transform:scale(0.8)} }
  .topic-info { text-align: center; font-size: 0.75rem; color: #555; margin-bottom: 20px; }
  .topic-info span { color: #f7b731; font-family: monospace; }
  .cards { display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; margin-bottom: 30px; }
  .card { background: #1a1a2e; border-radius: 20px; padding: 30px 40px; text-align: center; min-width: 180px; border: 1px solid #ffffff10; transition: transform 0.2s; }
  .card:hover { transform: translateY(-4px); }
  .card .icon { font-size: 2rem; margin-bottom: 10px; }
  .card .value { font-size: 3.5rem; font-weight: 700; line-height: 1; }
  .card .unit { font-size: 1.2rem; font-weight: 300; opacity: 0.6; }
  .card .label { font-size: 0.8rem; color: #666; margin-top: 8px; letter-spacing: 2px; }
  .temp .value { color: #ff6b6b; }
  .humi .value { color: #4ecdc4; }
  .qos-badge { display: inline-block; background: #f7b73120; color: #f7b731; border: 1px solid #f7b73150; border-radius: 8px; padding: 2px 8px; font-size: 0.7rem; margin-top: 6px; }
  .chart-wrap { background: #1a1a2e; border-radius: 20px; padding: 25px; margin: 0 auto 20px; max-width: 860px; border: 1px solid #ffffff10; }
  .chart-title { font-size: 0.75rem; color: #555; letter-spacing: 2px; margin-bottom: 15px; text-transform: uppercase; }
  canvas { width: 100% !important; display: block; }
  .log-wrap { background: #1a1a2e; border-radius: 20px; padding: 20px; margin: 0 auto 20px; max-width: 860px; border: 1px solid #ffffff10; }
  .log-title { font-size: 0.75rem; color: #555; letter-spacing: 2px; margin-bottom: 10px; }
  .log-list { font-family: monospace; font-size: 0.75rem; color: #4ecdc4; max-height: 120px; overflow-y: auto; }
  .log-list div { padding: 2px 0; border-bottom: 1px solid #ffffff05; }
  .test-btn { display: block; margin: 20px auto; padding: 10px 30px; background: #f7b731; color: #000; border: none; border-radius: 12px; font-size: 0.9rem; font-weight: 600; cursor: pointer; }
  .status { text-align: center; font-size: 0.8rem; color: #444; margin-top: 20px; }
  .status span { color: #4ecdc4; }
</style>
</head>
<body>
<h1>📡 MQTT Dashboard</h1>
<div class="badge"><span></span>MQTT → Flask → WebSocket 실시간 연동</div>
<div class="topic-info">브로커: <span>broker.emqx.io</span> | 토픽: <span>python/mqtt</span> | QoS: <span>1</span></div>
<div class="cards">
  <div class="card temp">
    <div class="icon">🌡️</div>
    <div class="value" id="temp">--</div>
    <div class="unit">°C</div>
    <div class="label">TEMPERATURE</div>
    <div class="qos-badge">QoS 1</div>
  </div>
  <div class="card humi">
    <div class="icon">💧</div>
    <div class="value" id="humi">--</div>
    <div class="unit">%</div>
    <div class="label">HUMIDITY</div>
    <div class="qos-badge">QoS 1</div>
  </div>
</div>
<div class="chart-wrap">
  <div class="chart-title">📈 온도 기록</div>
  <canvas id="tempChart"></canvas>
</div>
<div class="chart-wrap">
  <div class="chart-title">📈 습도 기록</div>
  <canvas id="humiChart"></canvas>
</div>
<div class="log-wrap">
  <div class="log-title">📋 MQTT 수신 로그</div>
  <div class="log-list" id="logList"></div>
</div>
<button class="test-btn" onclick="testPublish()">🚀 테스트 데이터 발행</button>
<div class="status">마지막 업데이트: <span id="time">-</span></div>
<script>
const socket = io();
socket.on('connect', () => console.log('✅ WebSocket 연결됨'));
socket.on('sensor_update', (data) => {
  const cur = data.current;
  const hist = data.history;
  document.getElementById('temp').textContent = parseFloat(cur.temperature).toFixed(1);
  document.getElementById('humi').textContent = parseFloat(cur.humidity).toFixed(1);
  document.getElementById('time').textContent = cur.timestamp || '-';
  const logList = document.getElementById('logList');
  const div = document.createElement('div');
  div.textContent = `[${cur.timestamp}] 온도: ${cur.temperature}°C, 습도: ${cur.humidity}%`;
  logList.prepend(div);
  while (logList.children.length > 20) logList.removeChild(logList.lastChild);
  updateCharts(hist);
});
socket.on('disconnect', () => { document.getElementById('time').textContent = '연결 끊김'; });
async function testPublish() {
  await fetch('/test');
}
function drawChart(canvasId, data, labels, color) {
  const canvas = document.getElementById(canvasId);
  const W = canvas.width = canvas.offsetWidth;
  const H = canvas.height = 130;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, W, H);
  if (data.length < 2) {
    ctx.fillStyle='#333'; ctx.font='13px sans-serif'; ctx.textAlign='center';
    ctx.fillText('데이터 수집 중...', W/2, H/2); return;
  }
  const pad = {top:15,bottom:25,left:38,right:10};
  const cW = W-pad.left-pad.right, cH = H-pad.top-pad.bottom;
  const min = Math.min(...data), max = Math.max(...data), range = max-min||1;
  const px = i => pad.left+(i/(data.length-1))*cW;
  const py = v => pad.top+cH-((v-min)/range)*cH;
  ctx.strokeStyle='#ffffff0d'; ctx.lineWidth=1;
  for(let i=0;i<=4;i++){
    const y=pad.top+(i/4)*cH;
    ctx.beginPath(); ctx.moveTo(pad.left,y); ctx.lineTo(W-pad.right,y); ctx.stroke();
    ctx.fillStyle='#555'; ctx.font='10px sans-serif'; ctx.textAlign='right';
    ctx.fillText((max-(i/4)*range).toFixed(1),pad.left-4,y+4);
  }
  ctx.fillStyle='#555'; ctx.font='9px sans-serif'; ctx.textAlign='center';
  const step=Math.ceil(labels.length/6);
  labels.forEach((l,i)=>{ if(i%step===0||i===labels.length-1) ctx.fillText(l,px(i),H-6); });
  ctx.beginPath(); ctx.moveTo(px(0),py(data[0]));
  data.forEach((v,i)=>ctx.lineTo(px(i),py(v)));
  ctx.lineTo(px(data.length-1),pad.top+cH); ctx.lineTo(px(0),pad.top+cH); ctx.closePath();
  ctx.fillStyle=color+'25'; ctx.fill();
  ctx.beginPath(); ctx.strokeStyle=color; ctx.lineWidth=2; ctx.lineJoin='round';
  data.forEach((v,i)=>i===0?ctx.moveTo(px(i),py(v)):ctx.lineTo(px(i),py(v))); ctx.stroke();
  data.forEach((v,i)=>{
    ctx.beginPath(); ctx.arc(px(i),py(v),i===data.length-1?5:2.5,0,Math.PI*2);
    ctx.fillStyle=i===data.length-1?'#fff':color; ctx.fill();
  });
}
function updateCharts(history) {
  const labels = history.map(d=>d.timestamp);
  drawChart('tempChart', history.map(d=>parseFloat(d.temperature)), labels, '#ff6b6b');
  drawChart('humiChart', history.map(d=>parseFloat(d.humidity)), labels, '#4ecdc4');
}
</script>
</body>
</html>
"""

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

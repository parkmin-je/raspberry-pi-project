import pymysql
import time
import threading
from flask import Flask, render_template, jsonify

app = Flask(__name__)

# ── DB 연결 ──────────────────────────────────
def get_connection():
    return pymysql.connect(
        host="localhost",
        user="sensor_user",
        password="1234",
        database="sensor_db",
        charset="utf8mb4"
    )

# ── 센서 읽기 (테스트용 랜덤 데이터) ──────────
def read_sensor():
    try:
        import random
        return {
            "temperature": round(random.uniform(18.0, 35.0), 1),
            "humidity":    round(random.uniform(40.0, 80.0), 1)
        }
    except Exception as e:
        print("센서 오류:", e)
        return None

# ── 오래된 데이터 자동 삭제 (미션 4) ──────────
MAX_RECORDS = 100

def cleanup_old_records():
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sensor_data")
    count = cursor.fetchone()[0]
    if count > MAX_RECORDS:
        delete_count = count - MAX_RECORDS
        cursor.execute(
            "DELETE FROM sensor_data ORDER BY measured_at ASC LIMIT %s",
            (delete_count,)
        )
        conn.commit()
        print(f"{delete_count}개 삭제됨 (현재 {MAX_RECORDS}개 유지)")
    cursor.close()
    conn.close()

# ── 데이터 저장 ──────────────────────────────
def save_to_db(temperature, humidity):
    conn   = get_connection()
    cursor = conn.cursor()
    sql    = "INSERT INTO sensor_data (temperature, humidity) VALUES (%s, %s)"
    cursor.execute(sql, (temperature, humidity))
    conn.commit()
    cursor.close()
    conn.close()
    cleanup_old_records()  # 미션 4 — 저장 후 정리

# ── 자동 수집 스레드 ─────────────────────────
TEMP_LIMIT = 30  # 미션 3 — 경보 기준 온도

def auto_collect(interval=10):
    while True:
        data = read_sensor()
        if data:
            save_to_db(data["temperature"], data["humidity"])
            print(f"저장됨: {data['temperature']}°C, {data['humidity']}%")
        time.sleep(interval)

# ── 메인 라우트 (미션 1, 2, 3 통합) ──────────
@app.route('/')
def index():
    conn   = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # 최근 10개 조회
    cursor.execute("SELECT * FROM sensor_data ORDER BY measured_at DESC LIMIT 10")
    records = cursor.fetchall()

    # 미션 1 — 통계 (AVG, MAX, MIN)
    cursor.execute("""
        SELECT
            AVG(temperature) AS avg_temp,
            MAX(temperature) AS max_temp,
            MIN(temperature) AS min_temp
        FROM sensor_data
    """)
    stats = cursor.fetchone()

    cursor.close()
    conn.close()

    # 미션 3 — 경보 확인
    alert = False
    if records and records[0]["temperature"] >= TEMP_LIMIT:
        alert = True

    return render_template("index.html",
                           records=records,
                           stats=stats,
                           alert=alert,
                           limit=TEMP_LIMIT)

# ── 데이터 수집 라우트 ───────────────────────
@app.route('/collect')
def collect():
    data = read_sensor()
    if data:
        save_to_db(data["temperature"], data["humidity"])
        return f"저장 완료: 온도 {data['temperature']}°C, 습도 {data['humidity']}%"
    else:
        return "센서 데이터를 읽을 수 없습니다.", 500

# ── 미션 5 — Chart.js API 라우트 ─────────────
@app.route('/api/chart')
def chart_data():
    conn   = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        SELECT temperature, humidity, measured_at
        FROM sensor_data
        ORDER BY measured_at ASC
        LIMIT 20
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    labels = [str(row["measured_at"]) for row in rows]
    temps  = [float(row["temperature"]) for row in rows]
    hums   = [float(row["humidity"])    for row in rows]

    return jsonify({"labels": labels, "temperatures": temps, "humidities": hums})

# ── 미션 6 — 시간대별 분석 라우트 ─────────────
@app.route('/analysis')
def analysis():
    conn   = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        SELECT
            HOUR(measured_at) AS hour,
            AVG(temperature)  AS avg_temp,
            COUNT(*)          AS count
        FROM sensor_data
        GROUP BY HOUR(measured_at)
        ORDER BY hour ASC
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("analysis.html", hourly=rows)

if __name__ == '__main__':
    thread = threading.Thread(target=auto_collect, args=(10,), daemon=True)
    thread.start()
    app.run(host="0.0.0.0", debug=True, use_reloader=False)

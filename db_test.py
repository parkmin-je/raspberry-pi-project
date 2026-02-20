import pymysql

conn = pymysql.connect(
    host="localhost",
    user="sensor_user",
    password="1234",
    database="sensor_db",
    charset="utf8mb4"
)

# Q1. fetchall() 형태 확인
cursor = conn.cursor(pymysql.cursors.DictCursor)
cursor.execute("SELECT * FROM sensor_data LIMIT 5")
rows = cursor.fetchall()
print("Q1. fetchall 결과 타입:", type(rows))
print("Q1. 첫번째 행 타입:", type(rows[0]))
print("Q1. 결과:", rows)
print()

# Q2. 일반 cursor vs DictCursor 비교
cursor2 = conn.cursor()
cursor2.execute("SELECT * FROM sensor_data LIMIT 1")
row2 = cursor2.fetchone()
print("Q2. 일반 cursor 결과:", row2)
print("Q2. 인덱스로 접근:", row2[1])
print()

cursor.close()
cursor2.close()
conn.close()
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-this'

# 간단한 사용자 저장소 (실제로는 데이터베이스 사용)
users = {}

@app.route('/')
def index():
    if 'username' in session:
        return f'<h1>환영합니다, {session["username"]}님!</h1><a href="/logout">로그아웃</a>'
    return '<h1>Flask 회원가입/로그인</h1><a href="/login">로그인</a> | <a href="/register">회원가입</a>'

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username in users:
            flash('이미 존재하는 사용자입니다.')
            return redirect(url_for('register'))
        
        users[username] = generate_password_hash(password)
        flash('회원가입 성공! 로그인해주세요.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username not in users:
            flash('존재하지 않는 사용자입니다.')
            return redirect(url_for('login'))
        
        if check_password_hash(users[username], password):
            session['username'] = username
            flash('로그인 성공!')
            return redirect(url_for('index'))
        else:
            flash('비밀번호가 틀렸습니다.')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('로그아웃되었습니다.')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

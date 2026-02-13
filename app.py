from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, EmailField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import re

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_ENABLED'] = False

db = SQLAlchemy(app)

# 팔로우 관계 테이블
followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

# 데이터베이스 모델
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    profile = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 관계
    tweets = db.relationship('Tweet', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    
    # 팔로우 관계
    following = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'),
        lazy='dynamic'
    )
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def follow(self, user):
        if not self.is_following(user):
            self.following.append(user)
    
    def unfollow(self, user):
        if self.is_following(user):
            self.following.remove(user)
    
    def is_following(self, user):
        return self.following.filter(followers.c.followed_id == user.id).count() > 0
    
    def get_timeline(self):
        followed_tweets = Tweet.query.join(
            followers, (followers.c.followed_id == Tweet.user_id)
        ).filter(followers.c.follower_id == self.id)
        
        own_tweets = Tweet.query.filter_by(user_id=self.id)
        
        return followed_tweets.union(own_tweets).order_by(Tweet.created_at.desc())
    
    def unread_notifications_count(self):
        return Notification.query.filter_by(user_id=self.id, is_read=False).count()
    
    def unread_messages_count(self):
        return Message.query.filter_by(receiver_id=self.id, is_read=False).count()

class Tweet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(300), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def likes_count(self):
        return Like.query.filter_by(tweet_id=self.id).count()
    
    def retweets_count(self):
        return Retweet.query.filter_by(tweet_id=self.id).count()
    
    def replies_count(self):
        return Reply.query.filter_by(tweet_id=self.id).count()
    
    def is_liked_by(self, user):
        return Like.query.filter_by(user_id=user.id, tweet_id=self.id).first() is not None
    
    def is_retweeted_by(self, user):
        return Retweet.query.filter_by(user_id=user.id, tweet_id=self.id).first() is not None
    
    def is_bookmarked_by(self, user):
        return Bookmark.query.filter_by(user_id=user.id, tweet_id=self.id).first() is not None

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tweet_id = db.Column(db.Integer, db.ForeignKey('tweet.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'tweet_id', name='unique_like'),)

class Retweet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tweet_id = db.Column(db.Integer, db.ForeignKey('tweet.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'tweet_id', name='unique_retweet'),)

class Reply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(300), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tweet_id = db.Column(db.Integer, db.ForeignKey('tweet.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    author = db.relationship('User', backref='replies')

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    from_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tweet_id = db.Column(db.Integer, db.ForeignKey('tweet.id'), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', foreign_keys=[user_id], backref='notifications')
    from_user = db.relationship('User', foreign_keys=[from_user_id])

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')

class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tweet_id = db.Column(db.Integer, db.ForeignKey('tweet.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'tweet_id', name='unique_bookmark'),)

# 폼 검증
class RegisterForm(FlaskForm):
    username = StringField('아이디', validators=[
        DataRequired(message='아이디를 입력해주세요'),
        Length(min=4, max=20, message='아이디는 4-20자 사이여야 합니다')
    ])
    name = StringField('이름', validators=[
        DataRequired(message='이름을 입력해주세요'),
        Length(min=2, max=100, message='이름은 2-100자 사이여야 합니다')
    ])
    email = EmailField('이메일', validators=[
        DataRequired(message='이메일을 입력해주세요'),
        Email(message='올바른 이메일 형식이 아닙니다')
    ])
    profile = TextAreaField('프로필 소개', validators=[
        Length(max=200, message='프로필은 200자 이내로 작성해주세요')
    ])
    password = PasswordField('비밀번호', validators=[
        DataRequired(message='비밀번호를 입력해주세요'),
        Length(min=6, message='비밀번호는 최소 6자 이상이어야 합니다')
    ])
    confirm_password = PasswordField('비밀번호 확인', validators=[
        DataRequired(message='비밀번호를 다시 입력해주세요'),
        EqualTo('password', message='비밀번호가 일치하지 않습니다')
    ])
    
    def validate_username(self, username):
        if not re.match(r'^[a-zA-Z0-9_]+$', username.data):
            raise ValidationError('아이디는 영문, 숫자, 언더스코어만 사용 가능합니다')
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('이미 사용 중인 아이디입니다')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('이미 등록된 이메일입니다')

class LoginForm(FlaskForm):
    username = StringField('아이디', validators=[DataRequired(message='아이디를 입력해주세요')])
    password = PasswordField('비밀번호', validators=[DataRequired(message='비밀번호를 입력해주세요')])

class TweetForm(FlaskForm):
    content = TextAreaField('트윗', validators=[
        DataRequired(message='내용을 입력해주세요'),
        Length(max=300, message='트윗은 300자를 초과할 수 없습니다')
    ])

# 라우트
@app.route('/')
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        return render_template('dashboard.html', user=user)
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            name=form.name.data,
            email=form.email.data,
            profile=form.profile.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('회원가입이 완료되었습니다! 로그인해주세요.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            session['user_id'] = user.id
            session['username'] = user.username
            flash(f'{user.username}님, 환영합니다!', 'success')
            return redirect(url_for('timeline'))
        else:
            flash('아이디 또는 비밀번호가 올바르지 않습니다.', 'error')
    
    return render_template('login.html', form=form)

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('로그인이 필요합니다.', 'error')
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user)

@app.route('/timeline')
def timeline():
    if 'user_id' not in session:
        flash('로그인이 필요합니다.', 'error')
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    form = TweetForm()
    tweets = user.get_timeline().all()
    
    return render_template('timeline.html', user=user, tweets=tweets, form=form)

@app.route('/users')
def users_list():
    if 'user_id' not in session:
        flash('로그인이 필요합니다.', 'error')
        return redirect(url_for('login'))
    
    current_user = User.query.get(session['user_id'])
    all_users = User.query.filter(User.id != current_user.id).all()
    
    return render_template('users.html', user=current_user, all_users=all_users)

@app.route('/user/<username>')
def user_profile(username):
    if 'user_id' not in session:
        flash('로그인이 필요합니다.', 'error')
        return redirect(url_for('login'))
    
    current_user = User.query.get(session['user_id'])
    profile_user = User.query.filter_by(username=username).first_or_404()
    tweets = Tweet.query.filter_by(user_id=profile_user.id).order_by(Tweet.created_at.desc()).all()
    
    return render_template('user_profile.html', user=current_user, profile_user=profile_user, tweets=tweets)

@app.route('/notifications')
def notifications():
    if 'user_id' not in session:
        flash('로그인이 필요합니다.', 'error')
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    notifications = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc()).all()
    
    # 모든 알림을 읽음으로 표시
    for notif in notifications:
        notif.is_read = True
    db.session.commit()
    
    return render_template('notifications.html', user=user, notifications=notifications)

@app.route('/messages')
def messages():
    if 'user_id' not in session:
        flash('로그인이 필요합니다.', 'error')
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    # 대화 목록 가져오기
    conversations = db.session.query(User).join(
        Message, 
        db.or_(
            db.and_(Message.sender_id == user.id, Message.receiver_id == User.id),
            db.and_(Message.receiver_id == user.id, Message.sender_id == User.id)
        )
    ).distinct().all()
    
    return render_template('messages.html', user=user, conversations=conversations)

@app.route('/messages/<int:user_id>')
def message_thread(user_id):
    if 'user_id' not in session:
        flash('로그인이 필요합니다.', 'error')
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    other_user = User.query.get_or_404(user_id)
    
    # 두 사용자 간의 메시지 가져오기
    messages = Message.query.filter(
        db.or_(
            db.and_(Message.sender_id == user.id, Message.receiver_id == other_user.id),
            db.and_(Message.sender_id == other_user.id, Message.receiver_id == user.id)
        )
    ).order_by(Message.created_at.asc()).all()
    
    # 받은 메시지를 읽음으로 표시
    for msg in messages:
        if msg.receiver_id == user.id:
            msg.is_read = True
    db.session.commit()
    
    return render_template('message_thread.html', user=user, other_user=other_user, messages=messages)

@app.route('/bookmarks')
def bookmarks():
    if 'user_id' not in session:
        flash('로그인이 필요합니다.', 'error')
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    bookmarks = Bookmark.query.filter_by(user_id=user.id).order_by(Bookmark.created_at.desc()).all()
    tweets = [Tweet.query.get(b.tweet_id) for b in bookmarks]
    
    return render_template('bookmarks.html', user=user, tweets=tweets)

@app.route('/explore')
def explore():
    if 'user_id' not in session:
        flash('로그인이 필요합니다.', 'error')
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    # 모든 트윗을 최신순으로
    tweets = Tweet.query.order_by(Tweet.created_at.desc()).limit(50).all()
    
    return render_template('explore.html', user=user, tweets=tweets)

@app.route('/logout')
def logout():
    session.clear()
    flash('로그아웃되었습니다.', 'info')
    return redirect(url_for('index'))

# API 엔드포인트
@app.route('/api/tweet', methods=['POST'])
def api_tweet():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    content = data.get('content', '').strip()
    
    if not content:
        return jsonify({'error': 'Content is required'}), 400
    
    if len(content) > 300:
        return jsonify({'error': 'Tweet exceeds 300 characters'}), 400
    
    tweet = Tweet(content=content, user_id=session['user_id'])
    db.session.add(tweet)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'tweet': {
            'id': tweet.id,
            'content': tweet.content,
            'created_at': tweet.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
    }), 201

@app.route('/api/follow/<int:user_id>', methods=['POST'])
def api_follow(user_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    current_user = User.query.get(session['user_id'])
    user_to_follow = User.query.get(user_id)
    
    if not user_to_follow:
        return jsonify({'error': 'User not found'}), 404
    
    if current_user.id == user_id:
        return jsonify({'error': 'Cannot follow yourself'}), 400
    
    current_user.follow(user_to_follow)
    db.session.commit()
    
    # 알림 생성
    notif = Notification(
        user_id=user_to_follow.id,
        type='follow',
        from_user_id=current_user.id
    )
    db.session.add(notif)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Followed successfully'}), 200

@app.route('/api/unfollow/<int:user_id>', methods=['POST'])
def api_unfollow(user_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    current_user = User.query.get(session['user_id'])
    user_to_unfollow = User.query.get(user_id)
    
    if not user_to_unfollow:
        return jsonify({'error': 'User not found'}), 404
    
    current_user.unfollow(user_to_unfollow)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Unfollowed successfully'}), 200

@app.route('/api/like/<int:tweet_id>', methods=['POST'])
def api_like(tweet_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    tweet = Tweet.query.get_or_404(tweet_id)
    user = User.query.get(session['user_id'])
    
    existing_like = Like.query.filter_by(user_id=user.id, tweet_id=tweet_id).first()
    
    if existing_like:
        db.session.delete(existing_like)
        db.session.commit()
        return jsonify({'success': True, 'action': 'unliked', 'count': tweet.likes_count()}), 200
    else:
        like = Like(user_id=user.id, tweet_id=tweet_id)
        db.session.add(like)
        db.session.commit()
        
        # 알림 생성 (자신의 트윗이 아닌 경우)
        if tweet.user_id != user.id:
            notif = Notification(
                user_id=tweet.user_id,
                type='like',
                from_user_id=user.id,
                tweet_id=tweet_id
            )
            db.session.add(notif)
            db.session.commit()
        
        return jsonify({'success': True, 'action': 'liked', 'count': tweet.likes_count()}), 200

@app.route('/api/retweet/<int:tweet_id>', methods=['POST'])
def api_retweet(tweet_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    tweet = Tweet.query.get_or_404(tweet_id)
    user = User.query.get(session['user_id'])
    
    existing_retweet = Retweet.query.filter_by(user_id=user.id, tweet_id=tweet_id).first()
    
    if existing_retweet:
        db.session.delete(existing_retweet)
        db.session.commit()
        return jsonify({'success': True, 'action': 'unretweeted', 'count': tweet.retweets_count()}), 200
    else:
        retweet = Retweet(user_id=user.id, tweet_id=tweet_id)
        db.session.add(retweet)
        db.session.commit()
        
        # 알림 생성
        if tweet.user_id != user.id:
            notif = Notification(
                user_id=tweet.user_id,
                type='retweet',
                from_user_id=user.id,
                tweet_id=tweet_id
            )
            db.session.add(notif)
            db.session.commit()
        
        return jsonify({'success': True, 'action': 'retweeted', 'count': tweet.retweets_count()}), 200

@app.route('/api/bookmark/<int:tweet_id>', methods=['POST'])
def api_bookmark(tweet_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    tweet = Tweet.query.get_or_404(tweet_id)
    user = User.query.get(session['user_id'])
    
    existing_bookmark = Bookmark.query.filter_by(user_id=user.id, tweet_id=tweet_id).first()
    
    if existing_bookmark:
        db.session.delete(existing_bookmark)
        db.session.commit()
        return jsonify({'success': True, 'action': 'unbookmarked'}), 200
    else:
        bookmark = Bookmark(user_id=user.id, tweet_id=tweet_id)
        db.session.add(bookmark)
        db.session.commit()
        return jsonify({'success': True, 'action': 'bookmarked'}), 200

@app.route('/api/reply/<int:tweet_id>', methods=['POST'])
def api_reply(tweet_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    content = data.get('content', '').strip()
    
    if not content:
        return jsonify({'error': 'Content is required'}), 400
    
    if len(content) > 300:
        return jsonify({'error': 'Reply exceeds 300 characters'}), 400
    
    tweet = Tweet.query.get_or_404(tweet_id)
    user = User.query.get(session['user_id'])
    
    reply = Reply(content=content, user_id=user.id, tweet_id=tweet_id)
    db.session.add(reply)
    db.session.commit()
    
    # 알림 생성
    if tweet.user_id != user.id:
        notif = Notification(
            user_id=tweet.user_id,
            type='reply',
            from_user_id=user.id,
            tweet_id=tweet_id
        )
        db.session.add(notif)
        db.session.commit()
    
    return jsonify({'success': True}), 201

@app.route('/api/send_message/<int:user_id>', methods=['POST'])
def api_send_message(user_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    content = data.get('content', '').strip()
    
    if not content:
        return jsonify({'error': 'Content is required'}), 400
    
    receiver = User.query.get_or_404(user_id)
    sender = User.query.get(session['user_id'])
    
    message = Message(content=content, sender_id=sender.id, receiver_id=receiver.id)
    db.session.add(message)
    db.session.commit()
    
    return jsonify({'success': True}), 201

@app.route('/api/timeline', methods=['GET'])
def api_timeline():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = User.query.get(session['user_id'])
    tweets = user.get_timeline().all()
    
    return jsonify({
        'tweets': [{
            'id': tweet.id,
            'content': tweet.content,
            'author': tweet.author.username,
            'author_name': tweet.author.name,
            'created_at': tweet.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for tweet in tweets]
    }), 200

# 데이터베이스 초기화
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

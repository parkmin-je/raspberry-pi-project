from flask import Flask, request, jsonify

app = Flask(__name__)

# 메모리 저장소 (데이터베이스 대신)
app.users = {}  # {user_id: {id, name, email, password}}
app.tweets = []  # [{user_id, tweet}]
app.user_id_count = 0

@app.route('/ping', methods=['GET'])
def ping():
    """서버 상태 확인"""
    return 'pong'

@app.route('/sign-up', methods=['POST'])
def sign_up():
    """회원가입"""
    user_data = request.json
    
    # 필수 필드 검증
    if not user_data.get('email') or not user_data.get('password') or not user_data.get('name'):
        return '', 400
    
    # 이메일 중복 확인
    for user in app.users.values():
        if user['email'] == user_data['email']:
            return '', 400
    
    # 새 유저 생성
    app.user_id_count += 1
    new_user = {
        'id': app.user_id_count,
        'name': user_data['name'],
        'email': user_data['email'],
        'password': user_data['password'],
        'follow': []  # 팔로우 목록
    }
    
    app.users[app.user_id_count] = new_user
    
    return jsonify(new_user), 200

@app.route('/tweet', methods=['POST'])
def tweet():
    """트윗 작성"""
    tweet_data = request.json
    
    # 필수 필드 검증
    if not tweet_data.get('id') or not tweet_data.get('tweet'):
        return '', 400
    
    user_id = tweet_data['id']
    
    # 유저 존재 확인
    if user_id not in app.users:
        return '', 400
    
    # 트윗 길이 검증 (300자 제한)
    if len(tweet_data['tweet']) > 300:
        return '', 400
    
    # 트윗 저장
    new_tweet = {
        'user_id': user_id,
        'tweet': tweet_data['tweet']
    }
    app.tweets.append(new_tweet)
    
    return '', 200

@app.route('/follow', methods=['POST'])
def follow():
    """팔로우"""
    follow_data = request.json
    
    # 필수 필드 검증
    if not follow_data.get('id') or not follow_data.get('follow'):
        return '', 400
    
    user_id = follow_data['id']
    follow_id = follow_data['follow']
    
    # 유저 존재 확인
    if user_id not in app.users or follow_id not in app.users:
        return '', 400
    
    # 자기 자신을 팔로우하는 경우
    if user_id == follow_id:
        return '', 400
    
    # 팔로우 추가 (중복 방지)
    user = app.users[user_id]
    if follow_id not in user['follow']:
        user['follow'].append(follow_id)
    
    return '', 200

@app.route('/unfollow', methods=['POST'])
def unfollow():
    """언팔로우"""
    unfollow_data = request.json
    
    # 필수 필드 검증
    if not unfollow_data.get('id') or not unfollow_data.get('unfollow'):
        return '', 400
    
    user_id = unfollow_data['id']
    unfollow_id = unfollow_data['unfollow']
    
    # 유저 존재 확인
    if user_id not in app.users or unfollow_id not in app.users:
        return '', 400
    
    # 언팔로우
    user = app.users[user_id]
    if unfollow_id in user['follow']:
        user['follow'].remove(unfollow_id)
    
    return '', 200

@app.route('/timeline/<int:user_id>', methods=['GET'])
def timeline(user_id):
    """타임라인 조회 (본인 + 팔로우한 사람들의 트윗)"""
    # 유저 존재 확인
    if user_id not in app.users:
        return '', 400
    
    user = app.users[user_id]
    
    # 본인 + 팔로우한 사람들의 ID 목록
    timeline_user_ids = [user_id] + user['follow']
    
    # 해당 유저들의 트윗만 필터링
    timeline_tweets = [
        tweet for tweet in app.tweets
        if tweet['user_id'] in timeline_user_ids
    ]
    
    return jsonify({
        'user_id': user_id,
        'timeline': timeline_tweets
    }), 200

@app.route('/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """유저 정보 조회"""
    # 유저 존재 확인
    if user_id not in app.users:
        return '', 400
    
    user = app.users[user_id]
    
    return jsonify(user), 200

@app.route('/users', methods=['GET'])
def get_users():
    """전체 유저 목록 조회 (password 제외)"""
    users_list = [
        {key: value for key, value in user.items() if key != 'password'}
        for user in app.users.values()
    ]
    
    return jsonify(users_list), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
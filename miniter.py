from flask import Flask, request, jsonify, current_app
from flask.json.provider import DefaultJSONProvider
from sqlalchemy import create_engine, text

class CustomJSONProvider(DefaultJSONProvider):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return super().default(obj)

def insert_user(user):
    with current_app.database.connect() as conn:
        result = conn.execute(text("""
            INSERT INTO users (name, email, profile, hashed_password)
            VALUES (:name, :email, :profile, :password)
        """), user)
        conn.commit()
        return result.lastrowid

def get_user(user_id):
    with current_app.database.connect() as conn:
        user = conn.execute(text("""
            SELECT id, name, email, profile
            FROM users WHERE id = :user_id
        """), {'user_id': user_id}).fetchone()
    return {'id': user[0], 'name': user[1], 'email': user[2], 'profile': user[3]} if user else None

def get_all_users():
    with current_app.database.connect() as conn:
        users = conn.execute(text("""
            SELECT id, name, email, profile
            FROM users
        """)).fetchall()
    return [{'id': u[0], 'name': u[1], 'email': u[2], 'profile': u[3]} for u in users]

def delete_tweet(tweet_id):
    with current_app.database.begin() as conn:
        result = conn.execute(text("""
            DELETE FROM tweets WHERE id = :tweet_id
        """), {'tweet_id': tweet_id})
        return result.rowcount

def update_user(user_id, data):
    with current_app.database.begin() as conn:
        result = conn.execute(text("""
            UPDATE users
            SET name = :name, profile = :profile
            WHERE id = :user_id
        """), {'name': data['name'], 'profile': data['profile'], 'user_id': user_id})
        return result.rowcount

def create_app(test_config=None):
    app = Flask(__name__)
    app.json_provider_class = CustomJSONProvider
    app.json = CustomJSONProvider(app)
    if test_config is None:
        app.config.from_pyfile("config.py")
    else:
        app.config.update(test_config)
    database = create_engine(app.config['DB_URL'], max_overflow=0)
    app.database = database
    app.tweets = []

    @app.route("/ping", methods=['GET'])
    def ping():
        return "pong"

    @app.route("/sign-up", methods=['POST'])
    def sign_up():
        new_user = request.json
        new_user_id = insert_user(new_user)
        return jsonify(get_user(new_user_id))

    @app.route('/user/<int:user_id>', methods=['GET'])
    def get_user_info(user_id):
        user = get_user(user_id)
        if user is None:
            return '사용자가 존재하지 않습니다.', 404
        return jsonify(user)

    @app.route('/users', methods=['GET'])
    def user_list():
        return jsonify(get_all_users())

    @app.route('/tweet/<int:tweet_id>', methods=['DELETE'])
    def delete_tweet_endpoint(tweet_id):
        rows = delete_tweet(tweet_id)
        if rows == 0:
            return '트윗이 존재하지 않습니다.', 404
        return '', 200

    @app.route('/user/<int:user_id>', methods=['PUT'])
    def update_user_info(user_id):
        data = request.json
        rows = update_user(user_id, data)
        if rows == 0:
            return '사용자가 존재하지 않습니다.', 404
        return jsonify(get_user(user_id))

    return app

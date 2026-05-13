#!/usr/bin/env python3
"""
Mini App Backend API
Flask server for Telegram WebApp
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import hmac
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import Database

app = Flask(__name__, static_folder='webapp/build', static_url_path='')
CORS(app)

BOT_TOKEN = "7754411305:AAFUQsrXqUkWshJ1Jxc4919hchPIqKmemzk"
ADMIN_ID = 1079953976
db = Database()

def verify_telegram_webapp(init_data: str) -> dict | None:
    """Telegram WebApp init_data ni tekshirish"""
    try:
        params = {}
        for item in init_data.split('&'):
            if '=' in item:
                key, value = item.split('=', 1)
                params[key] = value
        
        hash_val = params.pop('hash', '')
        data_check = '\n'.join(f'{k}={v}' for k, v in sorted(params.items()))
        
        secret_key = hmac.new(b'WebAppData', BOT_TOKEN.encode(), hashlib.sha256).digest()
        computed = hmac.new(secret_key, data_check.encode(), hashlib.sha256).hexdigest()
        
        if hmac.compare_digest(computed, hash_val):
            if 'user' in params:
                import urllib.parse
                return json.loads(urllib.parse.unquote(params['user']))
        return None
    except Exception:
        return None

def get_user_from_request():
    """Request dan foydalanuvchini olish"""
    init_data = request.headers.get('X-Telegram-Init-Data', '')
    if init_data:
        user = verify_telegram_webapp(init_data)
        if user:
            return user
    
    # Dev mode - header dan user_id
    dev_user_id = request.headers.get('X-Dev-User-Id')
    if dev_user_id:
        return {'id': int(dev_user_id), 'first_name': 'Dev User'}
    
    return None

# ==================== API ROUTES ====================

@app.route('/api/me', methods=['GET'])
def get_me():
    user = get_user_from_request()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = user['id']
    db_user = db.get_user(user_id)
    
    return jsonify({
        'user_id': user_id,
        'first_name': user.get('first_name', ''),
        'username': user.get('username', ''),
        'is_admin': user_id == ADMIN_ID or db.is_admin(user_id),
        'is_banned': db.is_banned(user_id),
        'stats': db.get_user_results(user_id)[:5] if db_user else []
    })

@app.route('/api/tests', methods=['GET'])
def get_tests():
    user = get_user_from_request()
    tests = db.get_tests(approved_only=True)
    
    result = []
    for t in tests:
        result.append({
            'id': t['id'],
            'title': t['title'],
            'description': t['description'],
            'question_count': db.get_question_count(t['id']),
            'attempts': db.get_test_attempts(t['id']),
            'created_at': t['created_at']
        })
    
    return jsonify(result)

@app.route('/api/tests/<int:test_id>', methods=['GET'])
def get_test(test_id):
    test = db.get_test(test_id)
    if not test:
        return jsonify({'error': 'Not found'}), 404
    
    questions = db.get_questions(test_id)
    # Correct answer ni yashirish
    for q in questions:
        q.pop('correct_answer', None)
    
    return jsonify({
        'id': test['id'],
        'title': test['title'],
        'description': test['description'],
        'questions': questions
    })

@app.route('/api/tests/<int:test_id>/start', methods=['POST'])
def start_test(test_id):
    user = get_user_from_request()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    
    questions = db.get_questions(test_id)
    if not questions:
        return jsonify({'error': 'No questions'}), 404
    
    session_id = db.start_session(user['id'], test_id)
    
    return jsonify({
        'session_id': session_id,
        'questions': [
            {
                'id': q['id'],
                'question': q['question'],
                'options': q['options'],
                'explanation': q.get('explanation', '')
            }
            for q in questions
        ]
    })

@app.route('/api/tests/<int:test_id>/submit', methods=['POST'])
def submit_test(test_id):
    user = get_user_from_request()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    session_id = data.get('session_id')
    answers = data.get('answers', {})
    
    questions = db.get_questions(test_id)
    correct = 0
    results = []
    
    for q in questions:
        user_answer = answers.get(str(q['id']), -1)
        is_correct = user_answer == q['correct_answer']
        if is_correct:
            correct += 1
        results.append({
            'question_id': q['id'],
            'user_answer': user_answer,
            'correct_answer': q['correct_answer'],
            'is_correct': is_correct,
            'explanation': q.get('explanation', '')
        })
    
    total = len(questions)
    percentage = (correct / total * 100) if total > 0 else 0
    
    db.save_result(session_id, user['id'], test_id, correct, total)
    
    return jsonify({
        'correct': correct,
        'total': total,
        'percentage': round(percentage, 1),
        'results': results
    })

@app.route('/api/tests', methods=['POST'])
def create_test():
    user = get_user_from_request()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if db.is_banned(user['id']):
        return jsonify({'error': 'Banned'}), 403
    
    data = request.json
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    questions = data.get('questions', [])
    
    if not title:
        return jsonify({'error': 'Title required'}), 400
    if not questions:
        return jsonify({'error': 'Questions required'}), 400
    
    approved = user['id'] == ADMIN_ID or db.is_admin(user['id'])
    
    test_id = db.save_test(
        creator_id=user['id'],
        title=title,
        description=description,
        questions=questions,
        approved=approved
    )
    
    return jsonify({
        'id': test_id,
        'approved': approved,
        'message': 'Test created' if approved else 'Pending approval'
    })

@app.route('/api/rating', methods=['GET'])
def get_rating():
    top = db.get_top_users(20)
    return jsonify(top)

@app.route('/api/my-results', methods=['GET'])
def my_results():
    user = get_user_from_request()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    
    results = db.get_user_results(user['id'])
    return jsonify(results)

# ==================== ADMIN API ====================

def require_admin(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_user_from_request()
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401
        if user['id'] != ADMIN_ID and not db.is_admin(user['id']):
            return jsonify({'error': 'Forbidden'}), 403
        return f(*args, **kwargs)
    return decorated

@app.route('/api/admin/stats', methods=['GET'])
@require_admin
def admin_stats():
    period = request.args.get('period', 'all')
    
    if period == 'custom':
        start = request.args.get('start')
        end = request.args.get('end')
        stats = db.get_stats_custom_range(start, end)
    else:
        stats = db.get_stats_by_period(period) if period != 'all' else db.get_stats()
    
    return jsonify(stats)

@app.route('/api/admin/users', methods=['GET'])
@require_admin
def admin_users():
    period = request.args.get('period', 'all')
    
    if period != 'all':
        users = db.get_users_by_period(period)
    else:
        users = db.get_all_users_for_api()
    
    return jsonify(users)

@app.route('/api/admin/users/<int:user_id>/ban', methods=['POST'])
@require_admin
def ban_user(user_id):
    db.ban_user(user_id)
    return jsonify({'success': True})

@app.route('/api/admin/users/<int:user_id>/unban', methods=['POST'])
@require_admin
def unban_user(user_id):
    db.unban_user(user_id)
    return jsonify({'success': True})

@app.route('/api/admin/tests', methods=['GET'])
@require_admin
def admin_tests():
    tests = db.get_all_tests_for_api()
    return jsonify(tests)

@app.route('/api/admin/tests/<int:test_id>/approve', methods=['POST'])
@require_admin
def approve_test(test_id):
    db.approve_test(test_id)
    return jsonify({'success': True})

@app.route('/api/admin/tests/<int:test_id>/reject', methods=['POST'])
@require_admin
def reject_test(test_id):
    db.reject_test(test_id)
    return jsonify({'success': True})

@app.route('/api/admin/tests/<int:test_id>', methods=['DELETE'])
@require_admin
def delete_test(test_id):
    db.delete_test(test_id)
    return jsonify({'success': True})

@app.route('/api/admin/pending', methods=['GET'])
@require_admin
def pending_tests():
    tests = db.get_pending_tests()
    result = []
    for t in tests:
        creator = db.get_user(t['creator_id'])
        result.append({
            **t,
            'creator_name': creator['first_name'] if creator else 'Unknown',
            'question_count': db.get_question_count(t['id'])
        })
    return jsonify(result)

@app.route('/api/admin/broadcast', methods=['POST'])
@require_admin
async def broadcast():
    data = request.json
    message = data.get('message', '')
    
    if not message:
        return jsonify({'error': 'Message required'}), 400
    
    users = db.get_all_users()
    
    import asyncio
    from telegram import Bot
    bot = Bot(token="7754411305:AAFUQsrXqUkWshJ1Jxc4919hchPIqKmemzk")
    
    sent = 0
    failed = 0
    
    for u in users:
        try:
            await bot.send_message(chat_id=u['user_id'], text=message)
            sent += 1
        except Exception:
            failed += 1
    
    return jsonify({'sent': sent, 'failed': failed})

# ==================== STATIC FILES ====================

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

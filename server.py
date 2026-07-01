"""
Скоринговая оценка испытательного срока — сервер
Запуск: python3 server.py
"""
import json
import os
import secrets
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder='.')

# DATA_DIR берётся из переменной окружения (Railway volume) или из папки рядом со скриптом
DATA_DIR = os.environ.get('DATA_DIR', os.path.join(os.path.dirname(__file__), 'data'))
DATA_FILE = os.path.join(DATA_DIR, 'sessions.json')

# ── Storage ───────────────────────────────────────────────────────

def load_data():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    if not os.path.exists(DATA_FILE):
        save_data({'sessions': []})
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── Static files ───────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)

# ── Sessions ───────────────────────────────────────────────────────

@app.route('/api/sessions', methods=['GET'])
def list_sessions():
    data = load_data()
    summary = [{
        'id': s['id'],
        'employeeName': s['employeeName'],
        'createdBy': s.get('createdBy', ''),
        'expectedCount': s.get('expectedCount', 0),
        'responseCount': len(s.get('responses', [])),
        'createdAt': s['createdAt'],
    } for s in reversed(data['sessions'])]
    return jsonify({'sessions': summary})

@app.route('/api/sessions', methods=['POST'])
def create_session():
    body = request.get_json() or {}
    employee_name = (body.get('employeeName') or '').strip()
    if not employee_name:
        return jsonify({'error': 'Укажите имя сотрудника'}), 400

    data = load_data()
    session = {
        'id': secrets.token_hex(5),
        'adminKey': secrets.token_hex(10),
        'employeeName': employee_name,
        'createdBy': (body.get('createdBy') or '').strip(),
        'expectedCount': int(body.get('expectedCount') or 0),
        'createdAt': datetime.now().isoformat(),
        'responses': [],
    }
    data['sessions'].append(session)
    save_data(data)
    return jsonify({'session': session})

@app.route('/api/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    data = load_data()
    session = next((s for s in data['sessions'] if s['id'] == session_id), None)
    if not session:
        return jsonify({'error': 'Сессия не найдена'}), 404

    admin_key = request.args.get('adminKey', '')
    if admin_key == session['adminKey']:
        return jsonify({'session': session})
    else:
        return jsonify({'session': {
            'id': session['id'],
            'employeeName': session['employeeName'],
            'expectedCount': session.get('expectedCount', 0),
            'responseCount': len(session.get('responses', [])),
            'createdAt': session['createdAt'],
        }})

@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    body = request.get_json() or {}
    admin_key = body.get('adminKey', '')
    data = load_data()
    idx = next((i for i, s in enumerate(data['sessions']) if s['id'] == session_id), None)
    if idx is None:
        return jsonify({'error': 'Не найдена'}), 404
    if data['sessions'][idx]['adminKey'] != admin_key:
        return jsonify({'error': 'Неверный ключ'}), 403
    data['sessions'].pop(idx)
    save_data(data)
    return jsonify({'success': True})

# ── Responses ──────────────────────────────────────────────────────

@app.route('/api/sessions/<session_id>/responses', methods=['POST'])
def add_response(session_id):
    body = request.get_json() or {}
    respondent_name = (body.get('respondentName') or '').strip()
    if not respondent_name:
        return jsonify({'error': 'Укажите имя'}), 400

    data = load_data()
    idx = next((i for i, s in enumerate(data['sessions']) if s['id'] == session_id), None)
    if idx is None:
        return jsonify({'error': 'Сессия не найдена'}), 404

    session = data['sessions'][idx]
    dup = next((r for r in session.get('responses', [])
                if r['respondentName'].lower() == respondent_name.lower()), None)
    if dup:
        return jsonify({'error': 'Ответ от этого участника уже записан'}), 409

    response = {
        'id': secrets.token_hex(4),
        'respondentName': respondent_name,
        'gateAnswers': body.get('gateAnswers', {}),
        'answers': body.get('answers', {}),
        'gateFailed': bool(body.get('gateFailed', False)),
        'gateFailedAt': body.get('gateFailedAt'),
        'result': body.get('result'),
        'submittedAt': datetime.now().isoformat(),
    }
    session.setdefault('responses', []).append(response)
    save_data(data)
    return jsonify({'success': True, 'responseId': response['id']})

# ── Run ────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    print('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    print('🚀  Скоринговый инструмент запущен')
    print(f'\n    Откройте: http://localhost:{port}')
    print('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    print('Для остановки нажмите Ctrl+C\n')
    app.run(host='0.0.0.0', port=port, debug=False)

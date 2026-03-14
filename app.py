from flask import Flask, render_template, request, jsonify, redirect, url_for, session, render_template_string
from flask_limiter.errors import RateLimitExceeded
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from datetime import datetime, timedelta
from flask_limiter.util import get_remote_address
import sqlite3
import os
import json
import jwt
from functools import wraps
import hashlib
app = Flask(__name__)
app.secret_key = ''
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
csrf = CSRFProtect(app)
DATABASE = 'apice.db'
JWT_SECRET = ''
JWT_ALGORITHM = 'HS256'
limiter = Limiter(app=app, key_func=get_remote_address)
def init_db():
    db = sqlite3.connect(DATABASE, timeout=30.0, check_same_thread=False)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA busy_timeout = 30000')
    db.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name TEXT NOT NULL,
        grade INTEGER,
        class_num INTEGER,
        number INTEGER,
        role TEXT DEFAULT 'student',
        first_login INTEGER DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    hashed_password = hashlib.sha256('admin'.encode()).hexdigest()
    try:
        db.execute('''INSERT INTO users (username, password, name, role) 
                      VALUES (?, ?, ?, ?)''',
                   ('admin', hashed_password, '관리자', 'teacher'))
    except:
        pass
    db.execute('''CREATE TABLE IF NOT EXISTS experiments (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        max_participants INTEGER NOT NULL,
        created_by TEXT NOT NULL,
        created_by_id INTEGER,
        deadline DATETIME,
        total_sessions INTEGER DEFAULT 1,
        message_for_participants TEXT,
        subject TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        approved INTEGER DEFAULT 0,
        approved_by TEXT,
        approved_at DATETIME
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS experiment_sessions (
        id INTEGER PRIMARY KEY,
        experiment_id INTEGER NOT NULL,
        session_number INTEGER NOT NULL,
        session_date DATE NOT NULL,
        start_time TIME NOT NULL,
        end_time TIME NOT NULL,
        content TEXT,
        FOREIGN KEY (experiment_id) REFERENCES experiments(id)
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS participants (
        id INTEGER PRIMARY KEY,
        experiment_id INTEGER NOT NULL,
        user_id INTEGER,
        name TEXT NOT NULL,
        grade INTEGER,
        class_num INTEGER,
        number INTEGER,
        status TEXT DEFAULT 'pending',
        applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        approved_at DATETIME,
        FOREIGN KEY (experiment_id) REFERENCES experiments(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        message TEXT NOT NULL,
        related_experiment_id INTEGER,
        read_status INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (related_experiment_id) REFERENCES experiments(id)
    )''')
    db.commit()
    db.close()
def get_db():
    db = sqlite3.connect(DATABASE, timeout=30.0, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA busy_timeout = 30000')
    return db
@app.route('/api/csrf-token', methods=['GET'])
def get_csrf_token():
    """CSRF 토큰 반환"""
    return jsonify({'csrf_token': request.headers.get('X-CSRFToken', '')})
def create_jwt_token(user_id, username, name, role):
    """JWT 토큰 생성"""
    payload = {
        'user_id': user_id,
        'username': username,
        'name': name,
        'role': role,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(days=7)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token
def verify_jwt_token(token):
    """JWT 토큰 검증"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
def get_jwt_token_from_header():
    """요청 헤더에서 JWT 토큰 추출"""
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    return None
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' in session:
            return f(*args, **kwargs)
        token = get_jwt_token_from_header()
        if token:
            payload = verify_jwt_token(token)
            if payload:
                session['user_id'] = payload['user_id']
                session['username'] = payload['username']
                session['name'] = payload['name']
                session['role'] = payload['role']
                return f(*args, **kwargs)
        return redirect(url_for('login'))
    return decorated_function
def teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' in session:
            db = get_db()
            user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
            db.close()
            if user and user['role'] == 'teacher':
                return f(*args, **kwargs)
        token = get_jwt_token_from_header()
        if token:
            payload = verify_jwt_token(token)
            if payload and payload['role'] == 'teacher':
                session['user_id'] = payload['user_id']
                session['username'] = payload['username']
                session['name'] = payload['name']
                session['role'] = payload['role']
                return f(*args, **kwargs)
        return render_template_string("""
            <!DOCTYPE html>
            <html lang="ko">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <link rel='icon' type="image/png" href="https://raw.githubusercontent.com/Anion15/anion15.github.io/refs/heads/main/icon-.png">
                <title>어딜 감히! - Apice동아리</title>
            </head>
            <style>
                body {font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif !important;letter-spacing: -0.02em;overflow-x: hidden;background-color: #171717 translate="no"}
                html, body {overflow-x: hidden;position: relative;width: 100%;   -ms-overflow-style: none; scrollbar-width: none;}
                html ::-webkit-scrollbar {
                    display: none;
                }
            </style>
            <body>
                <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100vh; background-color: #f8f9fa; color: #333; font-family: Arial, sans-serif;">
                    <h1 style="font-size: 72px; margin-bottom: 0; text-align: center;">
                        선생님 전용 페이지입니다.
                    </h1>
                    <p style="font-size: 18px; margin-top: 10px;">
                        선생님께서는 로그인 후 이용해 주세요.
                    </p>
                    <br><br><br>
                    <a href="/login" style="font-size: 15px; color: #007bff; text-decoration: none; margin-top: 20px;">로그인 페이지로 이동</a>
                </div>
            </body>
            </html>
"""), 403
    return decorated_function
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per second")
@csrf.exempt
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        db.close()
        if user and hashlib.sha256(password.encode()).hexdigest() == user['password']:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['name'] = user['name']
            session['role'] = user['role']
            jwt_token = create_jwt_token(user['id'], user['username'], user['name'], user['role'])
            return jsonify({
                'success': True, 
                'role': user['role'],
                'token': jwt_token,
                'first_login': user['first_login']
            })
        else:
            return jsonify({'success': False, 'error': '아이디 또는 비밀번호가 올바르지 않습니다'}), 401
    return render_template('login.html')
@app.route('/logout')
@limiter.limit("10 per second")
def logout():
    session.clear()
    return redirect(url_for('index'))
@app.route('/change-password', methods=['GET', 'POST'])
@limiter.limit("10 per second")
@login_required
@csrf.exempt
def change_password():
    """비밀번호 변경 페이지"""
    if request.method == 'POST':
        data = request.get_json()
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
        if not new_password or not confirm_password:
            return jsonify({'success': False, 'error': '비밀번호를 입력해주세요'}), 400
        if new_password != confirm_password:
            return jsonify({'success': False, 'error': '신규 비밀번호가 일치하지 않습니다'}), 400
        if len(new_password) < 4:
            return jsonify({'success': False, 'error': '비밀번호는 최소 4자 이상이어야 합니다'}), 400
        db = get_db()
        hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
        db.execute(
            'UPDATE users SET password = ?, first_login = 0 WHERE id = ?',
            (hashed_password, session['user_id'])
        )
        db.commit()
        db.close()
        return jsonify({'success': True, 'message': '비밀번호가 변경되었습니다'})
    db = get_db()
    user = db.execute('SELECT first_login FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    db.close()
    if not user or not user['first_login']:
        return redirect(url_for('index'))
    return render_template('change_password.html')
@app.route('/api/user')
def get_user():
    if 'user_id' not in session:
        token = get_jwt_token_from_header()
        if token:
            payload = verify_jwt_token(token)
            if payload:
                return jsonify({
                    'logged_in': True,
                    'username': payload.get('username'),
                    'name': payload.get('name'),
                    'role': payload.get('role')
                })
        return jsonify({'logged_in': False})
    db = get_db()
    user = db.execute('SELECT id, username, name, grade, class_num, number, role FROM users WHERE id = ?', 
                      (session.get('user_id'),)).fetchone()
    db.close()
    if user:
        user_dict = dict(user)
        return jsonify({
            'logged_in': True,
            'id': user_dict.get('id'),
            'username': user_dict.get('username'),
            'name': user_dict.get('name'),
            'grade': user_dict.get('grade'),
            'class_num': user_dict.get('class_num'),
            'number': user_dict.get('number'),
            'role': user_dict.get('role')
        })
    return jsonify({'logged_in': False})
@app.route('/')
@limiter.limit("10 per second")
def index():
    return render_template('index.html')
@app.route('/api/experiments')
def get_experiments():
    """모든 승인된 실험계획서 조회"""
    from datetime import datetime
    now = datetime.now()
    db = get_db()
    experiments = db.execute(
        '''SELECT * FROM experiments 
           WHERE approved = 1 
           ORDER BY created_at DESC'''
    ).fetchall()
    db.close()
    result = []
    for exp in experiments:
        participants_count = count_participants(exp['id'])
        if exp['deadline']:
            deadline = datetime.fromisoformat(exp['deadline'])
            if now > deadline:
                status = '모집 종료'
            else:
                status = '모집중'
        else:
            status = '모집중'
        
        result.append({
            'id': exp['id'],
            'title': exp['title'],
            'description': exp['description'],
            'max_participants': exp['max_participants'],
            'created_by': exp['created_by'],
            'created_by_id': exp['created_by_id'],
            'deadline': exp['deadline'],
            'total_sessions': exp['total_sessions'],
            'message_for_participants': exp['message_for_participants'],
            'subject': exp['subject'],
            'status': status,
            'created_at': exp['created_at'],
            'participants_count': participants_count
        })
    
    return jsonify(result)

@app.route('/api/experiments/<int:exp_id>')
def get_experiment(exp_id):
    """특정 실험계획서 상세 조회"""
    db = get_db()
    exp = db.execute(
        'SELECT * FROM experiments WHERE id = ? AND approved = 1',
        (exp_id,)
    ).fetchone()
    
    if not exp:
        db.close()
        return jsonify({'error': '실험계획서를 찾을 수 없습니다'}), 404

    sessions = db.execute(
        'SELECT * FROM experiment_sessions WHERE experiment_id = ? ORDER BY session_number',
        (exp_id,)
    ).fetchall()

    user_participated = False
    if 'user_id' in session:
        participant = db.execute(
            'SELECT * FROM participants WHERE experiment_id = ? AND user_id = ?',
            (exp_id, session['user_id'])
        ).fetchone()
        user_participated = participant is not None
    
    db.close()
    
    participants = get_participants(exp_id)
    
    sessions_list = [dict(s) for s in sessions]

    now = datetime.now()
    current_session = None
    next_session = None
    all_sessions_completed = False
    
    if sessions_list:
        for i, sess in enumerate(sessions_list):
            try:
                session_datetime = datetime.fromisoformat(f"{sess['session_date']}T{sess['start_time']}")
                session_end_datetime = datetime.fromisoformat(f"{sess['session_date']}T{sess['end_time']}")

                if session_datetime <= now <= session_end_datetime:
                    current_session = sess
                    break

                elif session_datetime > now and next_session is None:
                    next_session = sess
            except:
                continue

        if sessions_list:
            last_session = sessions_list[-1]
            try:
                last_session_end = datetime.fromisoformat(f"{last_session['session_date']}T{last_session['end_time']}")
                if now > last_session_end:
                    all_sessions_completed = True
            except:
                pass
    
    return jsonify({
        'id': exp['id'],
        'title': exp['title'],
        'description': exp['description'],
        'max_participants': exp['max_participants'],
        'created_by': exp['created_by'],
        'deadline': exp['deadline'],
        'total_sessions': exp['total_sessions'],
        'message_for_participants': exp['message_for_participants'] if user_participated else '',
        'subject': exp['subject'],
        'created_at': exp['created_at'],
        'participants': participants,
        'participants_count': len(participants),
        'sessions': sessions_list,
        'user_participated': user_participated,
        'current_session': current_session,
        'next_session': next_session,
        'all_sessions_completed': all_sessions_completed
    })

@app.route('/regist', methods=['GET', 'POST'])
@limiter.limit("10 per second")
@login_required
@csrf.exempt
def register_experiment():
    """실험계획서 작성"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            deadline_str = data.get('deadline')
            sessions_list = data.get('sessions', [])
            
            if deadline_str and sessions_list:
                try:
                    deadline = datetime.fromisoformat(deadline_str)
                except:
                    return jsonify({'success': False, 'error': '모집 마감 일시 형식이 잘못되었습니다'}), 400
                
                session_datetimes = []
                for sess in sessions_list:
                    session_date = sess.get('date', '')
                    start_time = sess.get('start_time', '')
                    
                    if session_date and start_time:
                        try:
                            session_datetime = datetime.fromisoformat(f"{session_date}T{start_time}")
                            session_datetimes.append({
                                'number': sess.get('number'),
                                'datetime': session_datetime
                            })
                        except:
                            pass
                
                if session_datetimes:
                    first_session = min(session_datetimes, key=lambda x: x['datetime'])
                    if first_session['datetime'] < deadline:
                        return jsonify({'success': False, 'error': '모집 마감 일시보다 실험 일정이 앞서면 안됩니다.'}), 400

                    sorted_sessions = sorted(session_datetimes, key=lambda x: x['datetime'])
                    for i in range(len(sorted_sessions) - 1):
                        current_sess = sorted_sessions[i]
                        next_sess = sorted_sessions[i + 1]
                        
                        if current_sess['datetime'] > next_sess['datetime']:
                            return jsonify({'success': False, 'error': f"{current_sess['number']}번째 실험보다 {next_sess['number']}번째 실험 일정이 앞서면 안됩니다."}), 400
            
            db = get_db()
            cursor = db.execute('''INSERT INTO experiments 
                          (title, description, max_participants, deadline, total_sessions, 
                           message_for_participants, subject, created_by, created_by_id) 
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                       (data['title'], 
                        data['description'], 
                        int(data['max_participants']),
                        data.get('deadline'),
                        data.get('total_sessions', 1),
                        data.get('message_for_participants', ''),
                        data.get('subject', ''),
                        session['name'],
                        session['user_id']))
            
            exp_id = cursor.lastrowid

            sessions_list = data.get('sessions', [])
            for sess in sessions_list:
                db.execute('''INSERT INTO experiment_sessions
                             (experiment_id, session_number, session_date, start_time, end_time, content)
                             VALUES (?, ?, ?, ?, ?, ?)''',
                          (exp_id, 
                           sess.get('number'),
                           sess.get('date'),
                           sess.get('start_time'),
                           sess.get('end_time'),
                           sess.get('content')))

            user_info = db.execute('SELECT grade, class_num, number FROM users WHERE id = ?',
                                  (session['user_id'],)).fetchone()
            
            db.execute('''INSERT INTO participants
                         (experiment_id, user_id, name, grade, class_num, number, status)
                         VALUES (?, ?, ?, ?, ?, ?, ?)''',
                      (exp_id,
                       session['user_id'],
                       session['name'],
                       user_info['grade'] if user_info else None,
                       user_info['class_num'] if user_info else None,
                       user_info['number'] if user_info else None,
                       'approved'))
            
            db.commit()
            db.close()
            
            return jsonify({'success': True, 'message': '실험계획서가 작성되었습니다. 선생님 승인을 기다려주세요.', 'experiment_id': exp_id})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return render_template('register_experiment.html')

@app.route('/api/apply', methods=['POST'])
@csrf.exempt
def apply_experiment():
    """실험에 참여 신청 - 로그인 필수, 로그인된 정보 자동 사용"""
    if 'user_id' not in session:
        return jsonify({'error': '로그인이 필요합니다', 'login_required': True}), 401
    data = request.get_json()
    exp_id = data.get('experiment_id')
    user_id = session.get('user_id')
    
    if not exp_id:
        return jsonify({'error': '실험을 선택해주세요'}), 400
    
    db = get_db()

    user = db.execute('SELECT name, grade, class_num, number FROM users WHERE id = ?', 
                      (user_id,)).fetchone()
    
    if not user:
        db.close()
        return jsonify({'error': '사용자 정보를 찾을 수 없습니다'}), 404
    
    user_dict = dict(user)
    
    exp = db.execute('SELECT * FROM experiments WHERE id = ?', (exp_id,)).fetchone()
    if not exp:
        db.close()
        return jsonify({'error': '실험을 찾을 수 없습니다'}), 404
    
    exp_dict = dict(exp)
    
    participants_count = db.execute(
        'SELECT COUNT(*) as count FROM participants WHERE experiment_id = ? AND status = "approved"',
        (exp_id,)
    ).fetchone()['count']
    
    if participants_count >= exp_dict['max_participants']:
        db.close()
        return jsonify({'error': '정원이 가득 찼습니다'}), 400
    
    existing = db.execute(
        'SELECT * FROM participants WHERE experiment_id = ? AND user_id = ?',
        (exp_id, user_id)
    ).fetchone()
    
    if existing:
        db.close()
        return jsonify({'error': '이미 신청했습니다'}), 400
    
    db.execute('''INSERT INTO participants 
                  (experiment_id, user_id, name, grade, class_num, number, status) 
                  VALUES (?, ?, ?, ?, ?, ?, ?)''',
               (exp_id, user_id, user_dict.get('name'), user_dict.get('grade'), 
                user_dict.get('class_num'), user_dict.get('number'), 'pending'))
    db.commit()
    db.close()
    
    return jsonify({'success': True, 'message': '참여 신청이 완료되었습니다. 선생님 승인을 기다려주세요.'})

@app.route('/join', methods=['GET', 'POST'])
@limiter.limit("10 per second")
@csrf.exempt
def join_experiment():
    if request.method == 'POST':
        return apply_experiment()
    return render_template('join_experiment.html')

@app.route('/admin')
@limiter.limit("10 per second")
@teacher_required
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/api/admin/pending-experiments')
@teacher_required
def get_pending_experiments():
    db = get_db()
    experiments = db.execute(
        'SELECT * FROM experiments WHERE approved = 0 ORDER BY created_at DESC'
    ).fetchall()
    db.close()
    
    result = []
    for exp in experiments:
        result.append({
            'id': exp['id'],
            'title': exp['title'],
            'description': exp['description'],
            'max_participants': exp['max_participants'],
            'created_by': exp['created_by'],
            'created_at': exp['created_at']
        })
    
    return jsonify(result)

@app.route('/api/admin/pending-participants')
@teacher_required
def get_pending_participants():
    db = get_db()
    participants = db.execute('''
        SELECT p.*, e.title as experiment_title 
        FROM participants p
        JOIN experiments e ON p.experiment_id = e.id
        WHERE p.status = 'pending'
        ORDER BY p.applied_at DESC
    ''').fetchall()
    db.close()
    
    result = []
    for p in participants:
        result.append({
            'id': p['id'],
            'experiment_id': p['experiment_id'],
            'name': p['name'],
            'grade': p['grade'],
            'class': p['class_num'],
            'number': p['number'],
            'experiment_title': p['experiment_title'],
            'applied_at': p['applied_at']
        })
    
    return jsonify(result)

@app.route('/api/admin/approve-experiment/<int:exp_id>', methods=['POST'])
@teacher_required
@csrf.exempt
def approve_experiment(exp_id):
    data = request.get_json() or {}
    teacher_name = data.get('teacher_name', session.get('name', 'Admin'))
    
    db = get_db()
    exp = db.execute('SELECT * FROM experiments WHERE id = ?', (exp_id,)).fetchone()
    db.execute('''UPDATE experiments 
                  SET approved = 1, approved_by = ?, approved_at = CURRENT_TIMESTAMP 
                  WHERE id = ?''',
               (teacher_name, exp_id))
    
    if exp['created_by_id']:
        create_notification(db, exp['created_by_id'], 'experiment_approved',
                          f'"{exp["title"]}" 실험이 승인되었습니다!', exp_id)
    
    db.commit()
    db.close()
    
    return jsonify({'success': True, 'message': '실험이 승인되었습니다'})

@app.route('/api/admin/reject-experiment/<int:exp_id>', methods=['POST'])
@teacher_required
@csrf.exempt
def reject_experiment(exp_id):
    db = get_db()
    db.execute('DELETE FROM experiments WHERE id = ?', (exp_id,))
    db.commit()
    db.close()
    
    return jsonify({'success': True, 'message': '실험이 거절되었습니다'})

@app.route('/api/admin/approve-participant/<int:p_id>', methods=['POST'])
@teacher_required
@csrf.exempt
def approve_participant(p_id):
    data = request.get_json() or {}
    teacher_name = data.get('teacher_name', session.get('name', 'Admin'))
    
    db = get_db()

    participant = db.execute('SELECT * FROM participants WHERE id = ?', (p_id,)).fetchone()
    
    if not participant:
        db.close()
        return jsonify({'error': '참여자를 찾을 수 없습니다'}), 404

    exp = db.execute('SELECT * FROM experiments WHERE id = ?', (participant['experiment_id'],)).fetchone()
    current_count = db.execute(
        'SELECT COUNT(*) as count FROM participants WHERE experiment_id = ? AND status = "approved"',
        (participant['experiment_id'],)
    ).fetchone()['count']
    
    if current_count >= exp['max_participants']:
        db.close()
        return jsonify({'error': '정원이 가득 찼습니다'}), 400
    
    db.execute('''UPDATE participants 
                  SET status = 'approved', approved_at = CURRENT_TIMESTAMP 
                  WHERE id = ?''', (p_id,))
    
    if participant['user_id']:
        create_notification(db, participant['user_id'], 'participant_approved',
                          f'"{exp["title"]}" 실험 참여가 승인되었습니다!', participant['experiment_id'])
    db.commit()
    db.close()
    
    return jsonify({'success': True, 'message': '참여자가 승인되었습니다'})

@app.route('/api/admin/reject-participant/<int:p_id>', methods=['POST'])
@teacher_required
@csrf.exempt
def reject_participant(p_id):
    """참여자 거절"""
    db = get_db()
    db.execute('UPDATE participants SET status = "rejected" WHERE id = ?', (p_id,))
    db.commit()
    db.close()
    
    return jsonify({'success': True, 'message': '참여자가 거절되었습니다'})



@app.route('/api/admin/create-student', methods=['POST'])
@teacher_required
@csrf.exempt
def create_student():
    data = request.get_json()

    username = data.get('username')
    password = data.get('password')
    name = data.get('name')
    grade = data.get('grade')
    class_num = data.get('class')
    number = data.get('number')
    is_teacher = data.get('is_teacher', False)

    if isinstance(is_teacher, str):
        is_teacher = is_teacher.lower() == "true"

    if not all([username, password, name, grade, class_num, number]):
        return jsonify({'success': False, 'error': '모든 필드를 입력해주세요'}), 400

    if len(username) < 3 or len(password) < 4:
        return jsonify({
            'success': False,
            'error': '아이디는 3자 이상, 비밀번호는 4자 이상이어야 합니다'
        }), 400

    db = get_db()

    try:
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        role = 'teacher' if is_teacher else 'student'

        db.execute('''
            INSERT INTO users 
            (username, password, name, grade, class_num, number, role)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (username, hashed_password, name, grade, class_num, number, role))

        db.commit()
        db.close()

        return jsonify({'success': True, 'message': f'{name} 계정이 생성되었습니다.'})

    except sqlite3.IntegrityError:
        db.close()
        return jsonify({'success': False, 'error': '이미 존재하는 아이디입니다'}), 400

@app.route('/api/admin/students')
@teacher_required
def get_students():
    db = get_db()
    students = db.execute(
        'SELECT id, username, name, grade, class_num as class, number FROM users WHERE role = "student" ORDER BY grade, class_num, number'
    ).fetchall()
    db.close()
    
    result = []
    for s in students:
        result.append({
            'id': s['id'],
            'username': s['username'],
            'name': s['name'],
            'grade': s['grade'],
            'class': s['class'],
            'number': s['number']
        })
    
    return jsonify(result)

@app.route('/api/admin/delete-student/<int:student_id>', methods=['POST'])
@teacher_required
@csrf.exempt
def delete_student(student_id):
    db = get_db()
    db.execute('DELETE FROM users WHERE id = ? AND role = "student"', (student_id,))
    db.commit()
    db.close()
    
    return jsonify({'success': True, 'message': '계정이 삭제되었습니다'})


@app.route('/api/notifications')
def get_notifications():
    if 'user_id' not in session:
        return jsonify({'error': '로그인이 필요합니다'}), 401
    
    db = get_db()
    notifications = db.execute('''
        SELECT * FROM notifications 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT 10
    ''', (session['user_id'],)).fetchall()
    db.close()

    result = []
    for notif in notifications:
        result.append({
            'id': notif['id'],
            'type': notif['type'],
            'message': notif['message'],
            'related_experiment_id': notif['related_experiment_id'],
            'read_status': notif['read_status'],
            'created_at': notif['created_at']
        })
    
    return jsonify(result)

@app.route('/api/notifications/<int:notif_id>/read', methods=['POST'])
@csrf.exempt
def mark_notification_read(notif_id):
    """알림을 읽음 처리"""
    db = get_db()
    db.execute('UPDATE notifications SET read_status = 1 WHERE id = ?', (notif_id,))
    db.commit()
    db.close()
    
    return jsonify({'success': True})


@app.route('/api/admin/all-experiments')
@teacher_required
def get_all_experiments_admin():
    db = get_db()
    experiments = db.execute('''
        SELECT * FROM experiments 
        ORDER BY approved DESC, created_at DESC
    ''').fetchall()
    db.close()
    
    result = []
    for exp in experiments:
        result.append({
            'id': exp['id'],
            'title': exp['title'],
            'description': exp['description'],
            'max_participants': exp['max_participants'],
            'created_by': exp['created_by'],
            'created_by_id': exp['created_by_id'],
            'deadline': exp['deadline'],
            'total_sessions': exp['total_sessions'],
            'message_for_participants': exp['message_for_participants'],
            'approved': exp['approved'],
            'created_at': exp['created_at'],
            'approved_at': exp['approved_at'],
            'participants_count': count_participants(exp['id'])
        })
    
    return jsonify(result)

@app.route('/api/admin/edit-experiment/<int:exp_id>', methods=['POST'])
@teacher_required
@csrf.exempt
def edit_experiment(exp_id):
    data = request.get_json()
    
    db = get_db()
    db.execute('''UPDATE experiments 
                  SET title = ?, description = ?, max_participants = ?, 
                      deadline = ?, total_sessions = ?, message_for_participants = ?
                  WHERE id = ?''',
               (data.get('title'),
                data.get('description'),
                data.get('max_participants'),
                data.get('deadline'),
                data.get('total_sessions'),
                data.get('message_for_participants'),
                exp_id))
    db.commit()
    db.close()
    
    return jsonify({'success': True, 'message': '실험 정보가 수정되었습니다'})

@app.route('/api/admin/delete-experiment/<int:exp_id>', methods=['POST'])
@teacher_required
@csrf.exempt
def delete_experiment(exp_id):
    db = get_db()
    db.execute('DELETE FROM experiments WHERE id = ?', (exp_id,))
    db.execute('DELETE FROM participants WHERE experiment_id = ?', (exp_id,))
    db.execute('DELETE FROM experiment_sessions WHERE experiment_id = ?', (exp_id,))
    db.commit()
    db.close()
    
    return jsonify({'success': True, 'message': '실험이 삭제되었습니다'})

@app.route('/api/check-time-conflict', methods=['POST'])
@csrf.exempt
def check_time_conflict():
    data = request.get_json()
    session_date = data.get('date')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    exclude_exp_id = data.get('exclude_exp_id')
    
    db = get_db()
    
    query = '''
        SELECT COUNT(*) as count FROM experiment_sessions es
        JOIN experiments e ON es.experiment_id = e.id
        WHERE es.session_date = ? 
        AND ((es.start_time < ? AND es.end_time > ?) 
             OR (es.start_time >= ? AND es.start_time < ?))
        AND e.approved = 1
    '''
    
    params = [session_date, end_time, start_time, start_time, end_time]
    
    if exclude_exp_id:
        query += ' AND es.experiment_id != ?'
        params.append(exclude_exp_id)
    
    conflict_count = db.execute(query, params).fetchone()['count']
    db.close()
    
    return jsonify({'has_conflict': conflict_count > 0})


def create_notification(db, user_id, notif_type, message, exp_id=None):
    db.execute('''INSERT INTO notifications
                  (user_id, type, message, related_experiment_id)
                  VALUES (?, ?, ?, ?)''',
              (user_id, notif_type, message, exp_id))

def count_participants(exp_id):
    db = get_db()
    count = db.execute(
        'SELECT COUNT(*) as count FROM participants WHERE experiment_id = ? AND status = "approved"',
        (exp_id,)
    ).fetchone()['count']
    db.close()
    return count

def get_participants(exp_id):
    db = get_db()
    participants = db.execute(
        '''SELECT name, grade, class_num as class, number FROM participants 
           WHERE experiment_id = ? AND status = "approved"''',
        (exp_id,)
    ).fetchall()
    db.close()
    return [dict(p) for p in participants]

@app.errorhandler(404)
@limiter.limit("10 per second")
def page_not_found(e):
    page = request.path
    return render_template_string("""
            <!DOCTYPE html>
            <html lang="ko">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <link rel='icon' type="image/png" href="https://raw.githubusercontent.com/Anion15/anion15.github.io/refs/heads/main/icon-.png">
                <title>길을 잠깐 잃은 것 같아요 - Apice동아리</title>
            </head>
            <style>
                body {font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif !important;letter-spacing: -0.02em;overflow-x: hidden;background-color: #171717 translate="no"}
                html, body {overflow-x: hidden;position: relative;width: 100%;   -ms-overflow-style: none; scrollbar-width: none;}
                html ::-webkit-scrollbar {
                    display: none;
                }

            </style>
            <body>
                <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100vh; background-color: #f8f9fa; color: #333; font-family: Arial, sans-serif;">
                    <h1 style="font-size: 172px; margin-bottom: 0; text-align: center;">
                        404
                    </h1>
                    <p style="font-size: 18px; margin-top: 10px;">
                        찾으시는 페이지가 없거나 다른 곳으로 이동되었어요.
                    </p>
                    <br><br><br>
                    <a href="/" style="font-size: 15px; color: #007bff; text-decoration: none; margin-top: 20px;">홈으로 이동</a>
                </div>
            </body>
            </html>
"""), 404

@app.errorhandler(RateLimitExceeded)
def ratelimit_handler(e):
    return render_template_string("""
            <!DOCTYPE html>
            <html lang="ko">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <link rel='icon' type="image/png" href="https://raw.githubusercontent.com/Anion15/anion15.github.io/refs/heads/main/icon-.png">
                <title>잠시 숨을 고르고 있어요 - Apice동아리</title>
            </head>
            <style>
                body {font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif !important;letter-spacing: -0.02em;overflow-x: hidden;background-color: #171717 translate="no"}
                html, body {overflow-x: hidden;position: relative;width: 100%;   -ms-overflow-style: none; scrollbar-width: none;}
                html ::-webkit-scrollbar {
                    display: none;
                }

            </style>
            <body>
                <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100vh; background-color: #f8f9fa; color: #333; font-family: Arial, sans-serif;">
                    <h1 style="font-size: 172px; margin-bottom: 0; text-align: center;">
                        429
                    </h1>
                    <p style="font-size: 18px; margin-top: 10px;">
                        짧은 시간에 요청이 많이 들어와<br>
                        시스템이 잠시 속도를 조절하고 있습니다.
                    </p>
                    <br><br><br>
                    <a href="/" style="font-size: 15px; color: #007bff; text-decoration: none; margin-top: 20px;">홈으로 이동</a>
                </div>
            </body>
            </html>
"""), 429

@app.route('/invalid-subdomain')
@limiter.limit("10 per second")
def invalid_subdomain():
    return render_template_string("""
            <!DOCTYPE html>
            <html lang="ko">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <link rel='icon' type="image/png" href="https://raw.githubusercontent.com/Anion15/anion15.github.io/refs/heads/main/icon-.png">
                <title>잘못된 하위 도메인에 접속하셨습니다 - Apice동아리</title>
            </head>
            <style>
                body {font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif !important;letter-spacing: -0.02em;overflow-x: hidden;background-color: #171717 translate="no"}
                html, body {overflow-x: hidden;position: relative;width: 100%;   -ms-overflow-style: none; scrollbar-width: none;}
                html ::-webkit-scrollbar {
                    display: none;
                }

            </style>
            <body>
                <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100vh; background-color: #f8f9fa; color: #333; font-family: Arial, sans-serif;">
                    <h1 style="font-size: 72px; margin-bottom: 0; text-align: center;">
                        잘못된 하위 도메인에 접속하셨습니다.
                    </h1>
                    <p style="font-size: 18px; margin-top: 10px; text-align: center;">
                        입력하신 주소는 지원되지 않는 하위 도메인입니다.<br>
                        올바른 URL: <a href="https://www.apice.kr" style="color:#4e73df; text-decoration:none;">https://www.apice.kr</a>
                    </p>
                    <br><br><br>
                </div>
            </body>
            </html>
"""), 404

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8000, debug=True)

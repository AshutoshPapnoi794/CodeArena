import pandas as pd
from flask import Flask, render_template, abort, request, jsonify, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_session import Session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from datetime import timedelta, datetime, date
import json
import math
import os
import re

# --- APP CONFIGURATION ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_change_in_prod_987654321')

# --- 1. DATABASE CONFIG ---
database_url = os.environ.get('DATABASE_URL')

if database_url:
    # Render uses 'postgres://' but SQLAlchemy needs 'postgresql://'
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Fallback to SQLite
    RENDER_INSTANCE_DIR = os.environ.get('RENDER_INSTANCE_DIR', os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance'))
    if not os.path.exists(RENDER_INSTANCE_DIR):
        os.makedirs(RENDER_INSTANCE_DIR)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(RENDER_INSTANCE_DIR, 'dsa_progress.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- 2. SESSION SECURITY ---
app.config['SESSION_TYPE'] = 'sqlalchemy'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'dsa_auth:'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# --- INITIALIZE EXTENSIONS ---
db = SQLAlchemy(app)
app.config['SESSION_SQLALCHEMY'] = db 
bcrypt = Bcrypt(app)
migrate = Migrate(app, db)
server_session = Session(app)
csrf = CSRFProtect(app)

# Rate Limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["2000 per day", "500 per hour"],
    storage_uri="memory://"
)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.session_protection = "strong"
login_manager.login_message_category = "error"

DATA = pd.DataFrame()

# --- MODELS ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False, index=True)
    password = db.Column(db.String(128), nullable=False)
    solved_problems = db.relationship('SolvedProblem', backref='solver', lazy=True)
    notes = db.relationship('Note', backref='author', lazy=True)

class SolvedProblem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    problem_id = db.Column(db.Integer, nullable=False)
    solved_at = db.Column(db.DateTime, nullable=False, default=db.func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'problem_id', name='_user_problem_uc'),)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    problem_id = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=True) # Markdown content
    updated_at = db.Column(db.DateTime, nullable=False, default=db.func.now(), onupdate=db.func.now())
    __table_args__ = (db.UniqueConstraint('user_id', 'problem_id', name='_user_problem_note_uc'),)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ENSURE TABLES EXIST ---
with app.app_context():
    try:
        db.create_all()
        print("✅ Database tables created successfully.")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")

# --- DATA LOGIC ---
TOPIC_PRIORITY = [
    ("math-geometry", ["Geometry", "Math", "Number Theory"]),
    ("bit-manipulation", ["Bit Manipulation"]),
    ("2-d-dp", ["Matrix", "Memoization"]),
    ("1-d-dp", ["Dynamic Programming"]),
    ("advanced-graphs", ["Union Find", "Topological Sort", "Shortest Path", "Minimum Spanning Tree"]),
    ("graphs", ["Graph", "Breadth-First Search", "Depth-First Search"]),
    ("tries", ["Trie"]),
    ("backtracking", ["Backtracking"]),
    ("heap-priority-queue", ["Heap (Priority Queue)"]),
    ("trees", ["Tree", "Binary Tree", "Binary Search Tree"]),
    ("linked-list", ["Linked List"]),
    ("intervals", ["Intervals"]),
    ("sliding-window", ["Sliding Window"]),
    ("binary-search", ["Binary Search"]),
    ("stack", ["Stack", "Monotonic Stack"]),
    ("two-pointers", ["Two Pointers"]),
    ("greedy", ["Greedy"]),
    ("arrays-hashing", ["Array", "Hash Table", "String", "Prefix Sum"]) 
]

SLUG_TO_NAME_MAP = {
    "arrays-hashing": "Arrays & Hashing", "two-pointers": "Two Pointers", "stack": "Stack",
    "binary-search": "Binary Search", "sliding-window": "Sliding Window", "linked-list": "Linked List",
    "trees": "Trees", "tries": "Tries", "heap-priority-queue": "Heap / Priority Queue",
    "backtracking": "Backtracking", "intervals": "Intervals", "greedy": "Greedy",
    "advanced-graphs": "Advanced Graphs", "graphs": "Graphs", "1-d-dp": "1-D DP",
    "2-d-dp": "2-D DP", "bit-manipulation": "Bit Manipulation", "math-geometry": "Math & Geometry"
}

CLASSIC_PROBLEM_IDS = {1,2,3,5,11,15,17,19,20,21,22,23,33,42,46,49,53,56,57,70,75,76,78,79,98,102,103,104,105,121,125,128,133,139,141,146,152,198,199,200,206,207,208,215,235,236,238,239,295,297,322,416,560,621,704,973,1448}

def assign_primary_topic(tags):
    for slug, keywords in TOPIC_PRIORITY:
        if any(k in tags for k in keywords):
            return slug
    return None

def calculate_signal_score(row):
    sub_score = math.log1p(row.get('TotalSubmissions', 0)) * 3
    like_score = row.get('adjusted_like_ratio', 0)
    rate = row.get('AcceptanceRate', 0)
    acc_bonus = 0
    if row['Difficulty'] == 'Easy' and 60 < rate < 85: acc_bonus = 15
    elif row['Difficulty'] == 'Medium' and 40 < rate < 70: acc_bonus = 20
    elif row['Difficulty'] == 'Hard' and 30 < rate < 60: acc_bonus = 25
    classic_bonus = 40 if row['ID'] in CLASSIC_PROBLEM_IDS else 0
    return sub_score + (like_score * 0.5) + acc_bonus + classic_bonus

def load_data():
    global DATA
    try:
        if not os.path.exists('leetcode_with_submissions.csv'):
            print("❌ CSV File not found.")
            return
        df = pd.read_csv('leetcode_with_submissions.csv')
        df.rename(columns={'Acceptance Rate (%)':'AcceptanceRate','Premium Only':'PremiumOnly','Total Submissions':'TotalSubmissions'}, inplace=True)
        df = df[(df['Category'] == 'Algorithms') & (df['PremiumOnly'] == False)].copy()
        
        df['Topics'] = df['Topics'].fillna('').apply(lambda x: [t.strip() for t in x.split(',') if t.strip()])
        
        def parse_subs(x):
            s = str(x).upper().strip()
            if 'M' in s: return int(float(s.replace('M','')) * 1000000)
            if 'K' in s: return int(float(s.replace('K','')) * 1000)
            try: return int(float(s))
            except: return 0
            
        df['TotalSubmissions'] = df['TotalSubmissions'].fillna(0).apply(parse_subs)
        df['adjusted_like_ratio'] = df.apply(lambda r: (r['Likes']/(r['Likes']+r['Dislikes']))*min((r['Likes']+r['Dislikes'])/1000,1)*100 if (r['Likes']+r['Dislikes'])>0 else 0, axis=1)
        df['signal_score'] = df.apply(calculate_signal_score, axis=1)

        df['AssignedTopic'] = df['Topics'].apply(assign_primary_topic)
        df = df[df['AssignedTopic'].notna()]
        DATA = df
        print(f"✅ Data Loaded: {len(DATA)} problems.")
    except Exception as e:
        print(f"❌ Data Load Error: {e}")
        DATA = pd.DataFrame()

def get_curated_problems_for_topic(topic_slug):
    if DATA.empty: return []
    df_topic = DATA[DATA['AssignedTopic'] == topic_slug].copy()
    if df_topic.empty: return []
    df_topic = df_topic.sort_values(by='signal_score', ascending=False)
    limit = 60 
    e_lim, m_lim, h_lim = int(limit*0.3), int(limit*0.5), int(limit*0.2)
    final_df = pd.concat([
        df_topic[df_topic['Difficulty'] == 'Easy'].head(e_lim),
        df_topic[df_topic['Difficulty'] == 'Medium'].head(m_lim),
        df_topic[df_topic['Difficulty'] == 'Hard'].head(h_lim)
    ])
    diff_order = pd.CategoricalDtype(['Easy', 'Medium', 'Hard'], ordered=True)
    final_df['Difficulty'] = final_df['Difficulty'].astype(diff_order)
    final_df = final_df.sort_values(by=['Difficulty', 'signal_score'], ascending=[True, False])
    return final_df.to_dict('records')

load_data()

# --- AUTH ROUTES ---

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if current_user.is_authenticated: return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            session.clear() 
            login_user(user, remember=False)
            return redirect(request.args.get('next') or url_for('index'))
        else:
            flash('Invalid credentials.', 'error')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
@limiter.limit("3 per hour")
def signup():
    if current_user.is_authenticated: return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            flash('Username must be alphanumeric.', 'error'); return render_template('signup.html')
        if len(username) < 3 or len(username) > 20:
            flash('Username length must be 3-20.', 'error'); return render_template('signup.html')
        if len(password) < 8:
            flash('Password must be 8+ characters.', 'error'); return render_template('signup.html')
        if User.query.filter_by(username=username).first():
            flash('Username taken.', 'error')
        else:
            hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
            user = User(username=username, password=hashed_pw)
            db.session.add(user)
            db.session.commit()
            session.clear()
            login_user(user, remember=False)
            flash('Account created.', 'success')
            return redirect(url_for('index'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    logout_user()
    session.clear()
    response = redirect(url_for('login'))
    response.set_cookie('session', '', expires=0, path='/')
    response.set_cookie('remember_token', '', expires=0, path='/')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

# --- MAIN ROUTES ---

@app.route('/')
@login_required
def index():
    if DATA.empty: return "Data Error: Run helper.py", 500
    
    solved = SolvedProblem.query.filter_by(user_id=current_user.id).order_by(SolvedProblem.solved_at.asc()).all()
    
    activity_map = {}
    distinct_dates = set()
    for s in solved:
        d_str = s.solved_at.strftime('%Y-%m-%d')
        activity_map[d_str] = activity_map.get(d_str, 0) + 1
        distinct_dates.add(s.solved_at.date())
        
    sorted_dates = sorted(list(distinct_dates))
    current_streak = 0
    longest_streak = 0
    if sorted_dates:
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        if sorted_dates[-1] == today or sorted_dates[-1] == yesterday:
            current_streak = 1
            for i in range(len(sorted_dates)-1, 0, -1):
                if (sorted_dates[i] - sorted_dates[i-1]).days == 1: current_streak += 1
                else: break
        
        temp_streak = 1
        for i in range(1, len(sorted_dates)):
            if (sorted_dates[i] - sorted_dates[i-1]).days == 1: temp_streak += 1
            else:
                longest_streak = max(longest_streak, temp_streak)
                temp_streak = 1
        longest_streak = max(longest_streak, temp_streak)

    topic_problems_map = {slug: [p['ID'] for p in get_curated_problems_for_topic(slug)] for slug in SLUG_TO_NAME_MAP.keys()}
    
    return render_template('index.html', 
                         topic_problems_map=json.dumps(topic_problems_map),
                         activity_map=json.dumps(activity_map),
                         current_streak=current_streak,
                         longest_streak=longest_streak,
                         total_solved=len(solved))

@app.route('/topic/<topic_slug>')
@login_required
def topic_page(topic_slug):
    problems = get_curated_problems_for_topic(topic_slug)
    return render_template('topic.html', topic_name=SLUG_TO_NAME_MAP.get(topic_slug, "Topic"), problems=problems, topic_slug=topic_slug)

@app.route('/api/progress', methods=['GET'])
@login_required
def get_progress():
    solved = SolvedProblem.query.filter_by(user_id=current_user.id).all()
    return jsonify({str(p.problem_id): {'solved_at': p.solved_at.isoformat()} for p in solved})

@app.route('/api/progress/toggle', methods=['POST'])
@login_required
def toggle_progress():
    data = request.get_json()
    pid = data.get('problem_id')
    entry = SolvedProblem.query.filter_by(user_id=current_user.id, problem_id=int(pid)).first()
    if data.get('solved') and not entry:
        db.session.add(SolvedProblem(user_id=current_user.id, problem_id=int(pid)))
    elif not data.get('solved') and entry:
        db.session.delete(entry)
    db.session.commit()
    return jsonify({'status': 'success'})

# --- NOTE ROUTES ---

@app.route('/api/notes/<int:problem_id>', methods=['GET'])
@login_required
def get_note(problem_id):
    note = Note.query.filter_by(user_id=current_user.id, problem_id=problem_id).first()
    return jsonify({'content': note.content if note else ''})

@app.route('/api/notes/save', methods=['POST'])
@login_required
def save_note():
    data = request.get_json()
    problem_id = data.get('problem_id')
    content = data.get('content')
    
    note = Note.query.filter_by(user_id=current_user.id, problem_id=problem_id).first()
    if note:
        note.content = content
    else:
        new_note = Note(user_id=current_user.id, problem_id=problem_id, content=content)
        db.session.add(new_note)
    
    db.session.commit()
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True)
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
from sqlalchemy import text, or_
from datetime import timedelta, datetime, date
import json
import math
import os
import re
import random

# --- APP CONFIGURATION ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_change_in_prod_987654321')

# --- 1. DATABASE CONFIG ---
database_url = os.environ.get('DATABASE_URL')

if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
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
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production' # Only True in Prod
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# --- INITIALIZE EXTENSIONS ---
db = SQLAlchemy(app)
app.config['SESSION_SQLALCHEMY'] = db 
bcrypt = Bcrypt(app)
migrate = Migrate(app, db)
server_session = Session(app)
csrf = CSRFProtect(app)

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
    
    # SRS Fields
    next_review_at = db.Column(db.DateTime, nullable=True)
    srs_interval = db.Column(db.Float, default=1.0) # Days until next review
    
    __table_args__ = (db.UniqueConstraint('user_id', 'problem_id', name='_user_problem_uc'),)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    problem_id = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=db.func.now(), onupdate=db.func.now())
    __table_args__ = (db.UniqueConstraint('user_id', 'problem_id', name='_user_problem_note_uc'),)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ENSURE TABLES & COLUMNS EXIST ---
with app.app_context():
    try:
        db.create_all()
        inspector = db.inspect(db.engine)
        columns = [c['name'] for c in inspector.get_columns('solved_problem')]
        if 'next_review_at' not in columns:
            print("⚠️ Migrating Database: Adding next_review_at column...")
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE solved_problem ADD COLUMN next_review_at DATETIME"))
                conn.execute(text("ALTER TABLE solved_problem ADD COLUMN srs_interval FLOAT DEFAULT 1.0"))
                conn.commit()
        print("✅ Database tables checked/created.")
    except Exception as e:
        print(f"❌ Database Init Error: {e}")

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

RADAR_GROUPS = {
    "Linear": ["arrays-hashing", "stack", "two-pointers", "sliding-window", "linked-list"],
    "Trees": ["trees", "tries", "heap-priority-queue"],
    "Graphs": ["graphs", "advanced-graphs", "backtracking"],
    "DP": ["1-d-dp", "2-d-dp"],
    "Search": ["binary-search", "greedy", "intervals"],
    "Logic": ["math-geometry", "bit-manipulation"]
}

# The "High Substance" List (Blind 75 / Grind 75 / NeetCode 150 favorites)
CLASSIC_PROBLEM_IDS = {1,2,3,5,11,15,17,19,20,21,22,23,33,42,46,49,53,56,57,70,75,76,78,79,98,102,103,104,105,121,125,128,133,139,141,146,152,198,199,200,206,207,208,215,235,236,238,239,295,297,322,416,560,621,704,973,1448}

def assign_primary_topic(tags):
    # Case-insensitive robust matching
    tags_lower = [t.lower() for t in tags]
    for slug, keywords in TOPIC_PRIORITY:
        for k in keywords:
            if k.lower() in tags_lower:
                return slug
    return None

def calculate_signal_score(row):
    """
    Substance Score Logic (Refined):
    1. Base: Log of submissions (Popularity) + Likes.
    2. Quality: Gaussian 'Sweet Spot' for acceptance rate (No cliff edges).
    3. Classic Multiplier: 2.5x boost for Classics (Ensures quality still matters).
    """
    # 1. Base Components (Popularity & Likes)
    sub_score = math.log1p(row.get('TotalSubmissions', 0)) * 2
    like_score = row.get('adjusted_like_ratio', 0) * 0.5
    
    # 2. Smooth Acceptance Bonus (Gaussian)
    # Replaces the rigid if/else blocks with a smooth curve
    rate = row.get('AcceptanceRate', 0)
    diff = row.get('Difficulty', 'Medium')
    
    # Define optimal "Fair" acceptance rates
    targets = {'Easy': 67.5, 'Medium': 52.5, 'Hard': 45.0}
    spreads = {'Easy': 17.5, 'Medium': 17.5, 'Hard': 15.0}
    
    optimal = targets.get(diff, 52.5)
    spread = spreads.get(diff, 17.5)
    
    # Calculate deviation from optimal (0 = perfect match)
    deviation = abs(rate - optimal) / spread
    # Max bonus 20, decays smoothly as rate moves away from optimal
    acc_bonus = max(0, 20 * math.exp(-deviation**2))
    
    base_score = sub_score + like_score + acc_bonus
    
    # 3. The Classic Multiplier (The Critical Fix)
    # Instead of adding +100, we multiply. This means a terrible classic 
    # won't necessarily beat an amazing non-classic.
    multiplier = 2.5 if row['ID'] in CLASSIC_PROBLEM_IDS else 1.0
    
    return base_score * multiplier

def load_data():
    global DATA
    try:
        if not os.path.exists('leetcode_with_submissions.csv'):
            print("❌ CSV File not found.")
            return
        df = pd.read_csv('leetcode_with_submissions.csv')
        df.rename(columns={'Acceptance Rate (%)':'AcceptanceRate','Premium Only':'PremiumOnly','Total Submissions':'TotalSubmissions'}, inplace=True)
        
        # Filter Algorithms & Free only
        df = df[(df['Category'] == 'Algorithms') & (df['PremiumOnly'] == False)].copy()
        
        # Parse Topics
        df['Topics'] = df['Topics'].fillna('').apply(lambda x: [t.strip() for t in x.split(',') if t.strip()])
        
        # Parse Submissions (handling '1.2M', '500K')
        def parse_subs(x):
            s = str(x).upper().strip()
            if 'M' in s: return int(float(s.replace('M','')) * 1000000)
            if 'K' in s: return int(float(s.replace('K','')) * 1000)
            try: return int(float(s))
            except: return 0
            
        df['TotalSubmissions'] = df['TotalSubmissions'].fillna(0).apply(parse_subs)
        
        # Calculate Adjusted Likes
        df['adjusted_like_ratio'] = df.apply(lambda r: (r['Likes']/(r['Likes']+r['Dislikes']))*min((r['Likes']+r['Dislikes'])/1000,1)*100 if (r['Likes']+r['Dislikes'])>0 else 0, axis=1)
        
        # Topic Assignment
        df['AssignedTopic'] = df['Topics'].apply(assign_primary_topic)
        df = df[df['AssignedTopic'].notna()]
        
        # Calculate Final Signal Score
        df['signal_score'] = df.apply(calculate_signal_score, axis=1)
        
        DATA = df
        print(f"✅ Data Loaded: {len(DATA)} problems.")
    except Exception as e:
        print(f"❌ Data Load Error: {e}")
        DATA = pd.DataFrame()

# --- TOPIC ROADMAP CACHE ---
TOPIC_CACHE = {}

def get_curated_problems_for_topic(topic_slug):
    """
    GAME DESIGN PROGRESSION LOGIC (v2)
    -----------------------------
    1. Tutorial: 2 Easy -> 1 Medium
    2. Adaptive Wave: Adjusts difficulty pattern based on the topic's inventory.
    """
    if topic_slug in TOPIC_CACHE: return TOPIC_CACHE[topic_slug]
    if DATA.empty: return []

    df_topic = DATA[DATA['AssignedTopic'] == topic_slug].copy()
    if df_topic.empty: return []

    # 1. Bucket and Sort by Signal Score
    pool_e = df_topic[df_topic['Difficulty'] == 'Easy'].sort_values('signal_score', ascending=False).to_dict('records')
    pool_m = df_topic[df_topic['Difficulty'] == 'Medium'].sort_values('signal_score', ascending=False).to_dict('records')
    pool_h = df_topic[df_topic['Difficulty'] == 'Hard'].sort_values('signal_score', ascending=False).to_dict('records')

    # 2. Determine Adaptive Pattern (Inventory Check)
    total_problems = len(pool_e) + len(pool_m) + len(pool_h)
    hard_ratio = len(pool_h) / total_problems if total_problems > 0 else 0
    
    if hard_ratio > 0.25:
        # Abundance of Hards: Standard Game Loop
        wave_pattern = ['Medium', 'Medium', 'Hard', 'Easy']
    elif hard_ratio > 0.10:
        # Moderate Hards: Spaced out Boss fights
        wave_pattern = ['Medium', 'Medium', 'Medium', 'Hard', 'Easy']
    else:
        # Conservation Mode: Rarely use Hards
        wave_pattern = ['Medium', 'Easy', 'Medium', 'Medium', 'Hard', 'Easy']

    roadmap = []
    
    def pop_best(difficulty_tier):
        """Attempts to pop from specific tier, with intelligent fallbacks."""
        if difficulty_tier == 'Easy':
            if pool_e: return pool_e.pop(0)
            if pool_m: return pool_m.pop(0) # Fallback: Doable Medium
            if pool_h: return pool_h.pop(0) # Fallback: Only Hards left
        elif difficulty_tier == 'Medium':
            if pool_m: return pool_m.pop(0)
            if pool_e: return pool_e.pop(0) # Fallback: Easy
            if pool_h: return pool_h.pop(0) # Fallback: Hard
        elif difficulty_tier == 'Hard':
            if pool_h: return pool_h.pop(0)
            if pool_m: return pool_m.pop(0) # Fallback: A chunky Medium
            if pool_e: return pool_e.pop(0) # Fallback: Easy
        return None

    # --- PHASE 1: THE TUTORIAL ---
    for _ in range(2):
        p = pop_best('Easy')
        if p: roadmap.append(p)
    
    p = pop_best('Medium')
    if p: roadmap.append(p)

    # --- PHASE 2: THE ADAPTIVE WAVE ---
    MAX_ITEMS = 60
    idx = 0
    pattern_len = len(wave_pattern)
    
    while (pool_e or pool_m or pool_h) and len(roadmap) < MAX_ITEMS:
        target_diff = wave_pattern[idx % pattern_len]
        problem = pop_best(target_diff)
        
        if problem:
            if problem['ID'] not in [x['ID'] for x in roadmap]:
                roadmap.append(problem)
        else:
            break
            
        idx += 1

    TOPIC_CACHE[topic_slug] = roadmap
    return roadmap

def get_problem_details(pid):
    if DATA.empty: return None
    row = DATA[DATA['ID'] == int(pid)]
    if row.empty: return None
    return row.iloc[0].to_dict()

load_data()

# --- NARRATIVE SRS TEMPLATES ---
SRS_STORIES = [
    "ALERT: Unauthorized entity '{title}' breached containment sector 4.",
    "CRITICAL: Memory fragment '{title}' decaying. Reinforcement required.",
    "WARNING: Rogue algorithm '{title}' detected in the subnet.",
    "SECURITY: Firewall penetration detected by '{title}'.",
    "GLITCH: Data corruption found in '{title}'. Manual override necessary.",
    "ANOMALY: Ghost process '{title}' consuming system resources.",
    "SYSTEM: Cognitive index for '{title}' below threshold.",
    "DANGER: Sentient code segment '{title}' attempting to escape."
]

def get_srs_missions(user_id):
    now = datetime.utcnow()
    # Fetch tasks where review date is passed OR null
    tasks = SolvedProblem.query.filter(
        SolvedProblem.user_id == user_id,
        or_(SolvedProblem.next_review_at <= now, SolvedProblem.next_review_at == None)
    ).order_by(SolvedProblem.next_review_at.asc()).limit(2).all()
    
    missions = []
    for t in tasks:
        p_details = get_problem_details(t.problem_id)
        if p_details:
            template = random.choice(SRS_STORIES)
            missions.append({
                "problem_id": t.problem_id,
                "title": p_details['Title'],
                "link": p_details['Link'],
                "story": template.format(title=p_details['Title'].upper()),
                "difficulty": p_details['Difficulty']
            })
    return missions

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
    return redirect(url_for('login'))

# --- MAIN ROUTES ---

@app.route('/')
@login_required
def index():
    if DATA.empty: return "Data Error: Run helper.py", 500
    
    solved_entries = SolvedProblem.query.filter_by(user_id=current_user.id).order_by(SolvedProblem.solved_at.asc()).all()
    solved_ids = {s.problem_id for s in solved_entries}
    
    # Heatmap & Streak Calculation
    activity_map = {}
    distinct_dates = set()
    for s in solved_entries:
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
        
        # Longest Streak logic
        temp_streak = 1
        for i in range(1, len(sorted_dates)):
            if (sorted_dates[i] - sorted_dates[i-1]).days == 1: temp_streak += 1
            else:
                longest_streak = max(longest_streak, temp_streak)
                temp_streak = 1
        longest_streak = max(longest_streak, temp_streak)

    # Pre-calculate topic maps for Radar
    topic_problems_map = {slug: [p['ID'] for p in get_curated_problems_for_topic(slug)] for slug in SLUG_TO_NAME_MAP.keys()}
    
    # Radar Data Generation
    radar_labels = []
    radar_data = []
    for group_name, slug_list in RADAR_GROUPS.items():
        total_in_group = 0
        solved_in_group = 0
        for slug in slug_list:
            if slug in topic_problems_map:
                p_ids = topic_problems_map[slug]
                total_in_group += len(p_ids)
                solved_in_group += sum(1 for pid in p_ids if pid in solved_ids)
        pct = (solved_in_group / total_in_group * 100) if total_in_group > 0 else 0
        radar_labels.append(group_name)
        radar_data.append(round(pct, 1))

    active_missions = get_srs_missions(current_user.id)

    return render_template('index.html', 
                         topic_problems_map=json.dumps(topic_problems_map),
                         activity_map=json.dumps(activity_map),
                         current_streak=current_streak,
                         longest_streak=longest_streak,
                         total_solved=len(solved_entries),
                         radar_labels=json.dumps(radar_labels),
                         radar_data=json.dumps(radar_data),
                         active_missions=active_missions)

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
        # First solve: Set review for tomorrow
        next_rev = datetime.utcnow() + timedelta(days=1)
        db.session.add(SolvedProblem(
            user_id=current_user.id, 
            problem_id=int(pid),
            next_review_at=next_rev,
            srs_interval=1.0
        ))
    elif not data.get('solved') and entry:
        db.session.delete(entry)
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/api/srs/resolve', methods=['POST'])
@login_required
def resolve_srs_mission():
    data = request.get_json()
    pid = data.get('problem_id')
    entry = SolvedProblem.query.filter_by(user_id=current_user.id, problem_id=int(pid)).first()
    
    if entry:
        # SRS Algorithm: x2.5 interval growth
        current_interval = float(entry.srs_interval or 1.0)
        new_interval = current_interval * 2.5
        
        # Add slight fuzz to prevent bunching
        fuzz = random.uniform(0.9, 1.1)
        actual_interval = math.ceil(new_interval * fuzz)
        
        entry.srs_interval = new_interval
        entry.next_review_at = datetime.utcnow() + timedelta(days=actual_interval)
        
        db.session.commit()
        return jsonify({'status': 'success', 'new_interval': actual_interval})
    return jsonify({'status': 'error'}), 404

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
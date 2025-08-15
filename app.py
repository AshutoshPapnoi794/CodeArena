import pandas as pd
from flask import Flask, render_template, abort, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
import json
import math
import ast
import os

# --- APP CONFIGURATION ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_very_secret_key_for_dev')

# Configure SQLite to use Render's persistent disk path if available, otherwise use a local 'instance' folder.
RENDER_INSTANCE_DIR = os.environ.get('RENDER_INSTANCE_DIR', os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance'))
if not os.path.exists(RENDER_INSTANCE_DIR):
    os.makedirs(RENDER_INSTANCE_DIR)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(RENDER_INSTANCE_DIR, 'dsa_progress.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- EXTENSIONS INITIALIZATION ---
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

DATA = pd.DataFrame()

# --- DATABASE MODELS ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    solved_problems = db.relationship('SolvedProblem', backref='solver', lazy=True)

class SolvedProblem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    problem_id = db.Column(db.Integer, nullable=False)
    solved_at = db.Column(db.DateTime, nullable=False, default=db.func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'problem_id', name='_user_problem_uc'),)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- DATA LOADING & SCORING LOGIC ---
THEMATIC_SUBTOPICS = { "arrays-hashing": [{"name": "Prefix Sum", "tags": ["Prefix Sum"]}, {"name": "Hash Table / Set Usage", "tags": ["Hash Table", "Counting"]}, {"name": "General Array & String Manipulation", "tags": ["Array", "String"]},], "two-pointers": [{"name": "Two Pointers", "tags": ["Two Pointers"]}], "stack": [{"name": "Monotonic Stack", "tags": ["Monotonic Stack"]}, {"name": "Core Stack Problems", "tags": ["Stack"]},], "binary-search": [{"name": "Binary Search", "tags": ["Binary Search"]}], "sliding-window": [{"name": "Monotonic Queue", "tags": ["Monotonic Queue"]}, {"name": "Sliding Window", "tags": ["Sliding Window"]},], "linked-list": [{"name": "Linked List", "tags": ["Linked List"]}], "trees": [{"name": "Binary Search Tree", "tags": ["Binary Search Tree"]}, {"name": "Traversal & Core Concepts (DFS/BFS)", "tags": ["Tree", "Binary Tree"]},], "graphs": [{"name": "Union Find", "tags": ["Union Find"]}, {"name": "Core Traversal (DFS/BFS)", "tags": ["Depth-First Search", "Breadth-First Search"]}, {"name": "General Graph Theory", "tags": ["Graph"]},], "1-d-dp": [{"name": "1-D Dynamic Programming", "tags": ["Dynamic Programming"]}], "2-d-dp": [{"name": "2-D Dynamic Programming", "tags": ["Dynamic Programming"]}], }
PROBLEM_LIMIT_PER_TOPIC=75; DIFFICULTY_QUOTAS={'Easy':0.35,'Medium':0.45,'Hard':0.20}; CLASSIC_PROBLEM_IDS={1,2,3,5,11,15,17,19,20,21,22,23,33,42,46,49,53,56,57,70,75,76,78,79,98,102,103,104,105,121,125,128,133,139,141,146,152,198,199,200,206,207,208,215,235,236,238,239,295,297,322,416,560,621,704,973,1448}; TOPIC_TIERS={'Array':0,'String':0,'Math':0,'Sorting':0,'Simulation':0,'Hash Table':1,'Two Pointers':1,'Stack':1,'Binary Search':1,'Sliding Window':1,'Linked List':1,'Queue':1,'Prefix Sum':1,'Counting':1,'Tree':2,'Binary Tree':2,'Binary Search Tree':2,'Depth-First Search':2,'Breadth-First Search':2,'Backtracking':2,'Recursion':2,'Greedy':3,'Dynamic Programming':3,'Graph':3,'Trie':3,'Union Find':3,'Heap (Priority Queue)':3,'Divide and Conquer':3,'Memoization':3,'Segment Tree':4,'Binary Indexed Tree':4,'Topological Sort':4,'Shortest Path':4,'Minimum Spanning Tree':4,'Line Sweep':4,'Ordered Set':4,'Monotonic Stack':4,'Monotonic Queue':4,'Bit Manipulation':5,'Geometry':5,'Combinatorics':5,'Number Theory':5,'Database':99,'Concurrency':99,'Interactive':99,'Shell':99}; PRIMARY_TOPIC_MAP={"Arrays & Hashing":["Array","Hash Table","String","Prefix Sum"],"Two Pointers":["Two Pointers"],"Stack":["Stack","Monotonic Stack"],"Binary Search":["Binary Search"],"Sliding Window":["Sliding Window","Monotonic Queue"],"Linked List":["Linked List"],"Trees":["Tree","Binary Tree","Binary Search Tree"],"Tries":["Trie"],"Heap / Priority Queue":["Heap (Priority Queue)"],"Backtracking":["Backtracking"],"Intervals":["Intervals"],"Greedy":["Greedy"],"Advanced Graphs":["Shortest Path","Topological Sort","Minimum Spanning Tree"],"Graphs":["Graph","Depth-First Search","Breadth-First Search","Union Find"],"1-D DP":["Dynamic Programming"],"2-D DP":["Dynamic Programming"],"Bit Manipulation":["Bit Manipulation"],"Math & Geometry":["Math","Geometry"]}; SLUG_TO_NAME_MAP={"arrays-hashing":"Arrays & Hashing","two-pointers":"Two Pointers","stack":"Stack","binary-search":"Binary Search","sliding-window":"Sliding Window","linked-list":"Linked List","trees":"Trees","tries":"Tries","heap-priority-queue":"Heap / Priority Queue","backtracking":"Backtracking","intervals":"Intervals","greedy":"Greedy","advanced-graphs":"Advanced Graphs","graphs":"Graphs","1-d-dp":"1-D DP","2-d-dp":"2-D DP","bit-manipulation":"Bit Manipulation","math-geometry":"Math & Geometry"}; ROADMAP_TOPIC_LEVEL={"Arrays & Hashing":1,"Two Pointers":1,"Stack":1,"Binary Search":1,"Sliding Window":1,"Linked List":1,"Trees":2,"Tries":3,"Heap / Priority Queue":3,"Backtracking":2,"Intervals":3,"Greedy":3,"Graphs":3,"Advanced Graphs":4,"1-D DP":3,"2-D DP":3,"Bit Manipulation":5,"Math & Geometry":5}; SPECIFIC_PATTERN_TAGS=set(sum([tags for name,tags in PRIMARY_TOPIC_MAP.items() if name not in["Arrays & Hashing","Math & Geometry"]],[]));
def adjusted_like_ratio(row): total_votes=row['Likes']+row['Dislikes']; return 0 if total_votes==0 else(row['Likes']/total_votes*min(total_votes/2000,1.0)*100);
def get_acceptance_rate_bonus(row): rate=row.get('AcceptanceRate',0); return 10 if(row['Difficulty']=='Easy'and 60<rate<85)or(row['Difficulty']=='Medium'and 40<rate<70)or(row['Difficulty']=='Hard'and 25<rate<50)else 0;
def parse_submissions(value):
    if pd.isna(value): return 0
    if isinstance(value,(int,float)): return int(value)
    value_str=str(value).strip().upper(); multiplier=1
    if value_str.endswith('K'): multiplier=1000; numeric_part_str=value_str[:-1]
    elif value_str.endswith('M'): multiplier=1000000; numeric_part_str=value_str[:-1]
    else: numeric_part_str=value_str
    try: numeric_value=float(numeric_part_str); return int(numeric_value*multiplier)
    except ValueError: return 0
def calculate_signal_score(row): submission_score=math.log1p(row.get('TotalSubmissions',0))*2.5; acceptance_bonus=get_acceptance_rate_bonus(row); classic_bonus=25 if row['ID']in CLASSIC_PROBLEM_IDS else 0; score=(row['adjusted_like_ratio']*0.4)+(submission_score*0.6)+classic_bonus+acceptance_bonus; return round(score,2)
def parse_similar_questions(similar_str):
    if not isinstance(similar_str,str)or not similar_str.startswith('['): return[]
    try: similar_list=json.loads(similar_str);
    except(json.JSONDecodeError,SyntaxError): return[]
    for item in similar_list:
        if'titleSlug'in item:item['Link']=f"https://leetcode.com/problems/{item['titleSlug']}/"
    return similar_list
def load_data():
    global DATA
    try:
        df=pd.read_csv('leetcode_with_submissions.csv');df.rename(columns={'Acceptance Rate (%)':'AcceptanceRate','Premium Only':'PremiumOnly','Total Submissions':'TotalSubmissions'},inplace=True)
        df=df[(df['Category']=='Algorithms')&(df['PremiumOnly']==False)].copy()
        df['Topics']=df['Topics'].fillna('').apply(lambda x:[t.strip()for t in x.split(',')if t.strip()]);df.loc[df['Title'].str.contains('Interval',case=False),'Topics']=df.loc[df['Title'].str.contains('Interval',case=False),'Topics'].apply(lambda x:x+['Intervals'])
        df['Difficulty']=pd.Categorical(df['Difficulty'],categories=['Easy','Medium','Hard'],ordered=True);df['TotalSubmissions']=df['TotalSubmissions'].fillna(0).apply(parse_submissions)
        df['SimilarQuestions']=df['Similar Questions'].fillna('[]').apply(parse_similar_questions);df['adjusted_like_ratio']=df.apply(adjusted_like_ratio,axis=1)
        df['prerequisite_tier']=df['Topics'].apply(lambda tl:max([TOPIC_TIERS.get(t,99)for t in tl]or[99]));df['signal_score']=df.apply(calculate_signal_score,axis=1)
        DATA=df;print(f"✅ LeetCode data loaded and scored. Total problems: {len(DATA)}")
    except FileNotFoundError:print("❌ ERROR: leetcode_with_submissions.csv not found.");DATA=pd.DataFrame()
def get_curated_problems_for_topic(topic_slug):
    graph_topic_name=SLUG_TO_NAME_MAP.get(topic_slug);
    if not graph_topic_name:return[]
    max_allowed_tier=ROADMAP_TOPIC_LEVEL.get(graph_topic_name,99);primary_tags=PRIMARY_TOPIC_MAP.get(graph_topic_name,[])
    mask=DATA['Topics'].apply(lambda topics:any(t in primary_tags for t in topics));base_df=DATA[mask&(DATA['prerequisite_tier']<=max_allowed_tier)].copy()
    if graph_topic_name=="Arrays & Hashing":base_df=base_df[~base_df['Topics'].apply(lambda topics:any(t in SPECIFIC_PATTERN_TAGS for t in topics))]
    elif graph_topic_name not in["Math & Geometry"]:other_specific_tags=SPECIFIC_PATTERN_TAGS-set(primary_tags);base_df=base_df[~base_df['Topics'].apply(lambda topics:any(t in other_specific_tags for t in topics))]
    if graph_topic_name=="1-D DP":base_df=base_df[~base_df['Topics'].apply(lambda x:'Matrix'in x)]
    elif graph_topic_name=="2-D DP":base_df=base_df[base_df['Topics'].apply(lambda x:'Matrix'in x)]
    if base_df.empty:return[]
    stratified_dfs=[];base_df=base_df.sort_values(by='signal_score',ascending=False)
    for difficulty,quota in DIFFICULTY_QUOTAS.items():limit=math.ceil(PROBLEM_LIMIT_PER_TOPIC*quota);difficulty_group=base_df[base_df['Difficulty']==difficulty];stratified_dfs.append(difficulty_group.head(limit))
    if not stratified_dfs:return[]
    curated_df=pd.concat(stratified_dfs).drop_duplicates(subset=['ID']);thematic_curriculum=THEMATIC_SUBTOPICS.get(topic_slug,[{"name":graph_topic_name,"tags":primary_tags}]);final_ordered_problems=[];processed_ids=set()
    for theme in thematic_curriculum:
        theme_tags=set(theme['tags']);theme_problems_mask=curated_df['Topics'].apply(lambda topics:any(tag in theme_tags for tag in topics));theme_df=curated_df[theme_problems_mask&~curated_df['ID'].isin(processed_ids)]
        if not theme_df.empty:theme_df_sorted=theme_df.sort_values(by=['Difficulty','signal_score'],ascending=[True,False]);final_ordered_problems.extend(theme_df_sorted.to_dict('records'));processed_ids.update(theme_df_sorted['ID'].tolist())
    return final_ordered_problems
load_data()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('index'))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and bcrypt.check_password_hash(user.password, request.form.get('password')):
            login_user(user, remember=True); next_page = request.args.get('next'); return redirect(next_page) if next_page else redirect(url_for('index'))
        else: flash('Login Unsuccessful. Please check username and password', 'error')
    return render_template('login.html')
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated: return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username'); password = request.form.get('password')
        if User.query.filter_by(username=username).first(): flash('Username already exists. Please choose a different one.', 'error'); return redirect(url_for('signup'))
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8'); user = User(username=username, password=hashed_password)
        db.session.add(user); db.session.commit(); flash('Your account has been created! You are now able to log in', 'success'); login_user(user, remember=True); return redirect(url_for('index'))
    return render_template('signup.html')
@app.route('/logout')
def logout(): logout_user(); return redirect(url_for('login'))
@app.route('/')
@login_required
def index():
    if DATA.empty: abort(500)
    topic_problems_map = {};
    for slug in SLUG_TO_NAME_MAP.keys(): curated_problems = get_curated_problems_for_topic(slug); topic_problems_map[slug] = [p['ID'] for p in curated_problems]
    problem_details = DATA.set_index('ID')[['Title', 'Difficulty', 'Link']].to_dict('index')
    return render_template('index.html', topic_problems_map=json.dumps(topic_problems_map), problem_details=json.dumps(problem_details))
@app.route('/topic/<topic_slug>')
@login_required
def topic_page(topic_slug):
    if DATA.empty: abort(500)
    problems_to_show = get_curated_problems_for_topic(topic_slug); graph_topic_name = SLUG_TO_NAME_MAP.get(topic_slug)
    if not graph_topic_name: abort(404)
    return render_template('topic.html', topic_name=graph_topic_name, problems=problems_to_show, total_count=len(problems_to_show), topic_slug=topic_slug)
@app.route('/api/progress', methods=['GET'])
@login_required
def get_progress():
    solved_problems = SolvedProblem.query.filter_by(user_id=current_user.id).all()
    solved_map = {str(p.problem_id): {'solved_at': p.solved_at.isoformat()} for p in solved_problems}
    return jsonify(solved_map)
@app.route('/api/progress/toggle', methods=['POST'])
@login_required
def toggle_progress():
    data = request.get_json(); problem_id = data.get('problem_id'); is_solved = data.get('solved')
    if problem_id is None or is_solved is None: return jsonify({'status': 'error', 'message': 'Missing data'}), 400
    problem_id = int(problem_id); existing_entry = SolvedProblem.query.filter_by(user_id=current_user.id, problem_id=problem_id).first()
    if is_solved and not existing_entry: new_solved = SolvedProblem(user_id=current_user.id, problem_id=problem_id); db.session.add(new_solved)
    elif not is_solved and existing_entry: db.session.delete(existing_entry)
    db.session.commit(); return jsonify({'status': 'success'})

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
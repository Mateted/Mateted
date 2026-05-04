from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import uuid

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SECRET_KEY'] = 'super_secret_key_for_sessions'
db = SQLAlchemy(app)

user_library = db.Table('user_library',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('mod_id', db.Integer, db.ForeignKey('mod.id'), primary_key=True)
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    reset_token = db.Column(db.String(100), nullable=True)
    saved_mods = db.relationship('Mod', secondary=user_library, backref=db.backref('users_who_saved', lazy='dynamic'))

class Mod(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mod_id = db.Column(db.String(100), unique=True, nullable=False)
    title = db.Column(db.String(100), nullable=False)
    creator = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    downloads = db.Column(db.Integer, default=0)
    logo_url = db.Column(db.String(300), default='')
    download_link = db.Column(db.String(300), default='')

with app.app_context():
    db.create_all()
    
    if Mod.query.count() < 500:
        print("\n Downloading mods ")
        try:
            geode_mods = []
            
            for page in range(1, 8):
                print(f"   -> Fetching page {page}...")
                url = f"https://api.geode-sdk.org/v1/mods?per_page=100&page={page}"
                response = requests.get(url)
                if response.status_code == 200:
                    geode_mods.extend(response.json().get('payload', {}).get('data', []))
            
            print(f"Saving {len(geode_mods)} mods to your database...")
            for item in geode_mods:
                mod_id = item.get('id', 'Unknown ID')
                mod_title = item.get('name') or item.get('title')
                dl_link = ""
                if item.get('versions') and len(item['versions']) > 0:
                    latest_version = item['versions'][0]
                    mod_title = mod_title or latest_version.get('name') or latest_version.get('title')
                    dl_link = latest_version.get('download_link', '')
                
                if not mod_title or mod_title == mod_id:
                    mod_title = mod_id.split('.')[-1].replace('-', ' ').title()
                
                mod_creator = "Unknown Creator"
                if isinstance(item.get('developer'), str):
                    mod_creator = item['developer']
                elif isinstance(item.get('developer'), dict):
                    mod_creator = item['developer'].get('display_name') or item['developer'].get('username') or "Unknown Creator"
                elif item.get('developers') and len(item['developers']) > 0:
                    first_dev = item['developers'][0]
                    if isinstance(first_dev, str):
                        mod_creator = first_dev
                    elif isinstance(first_dev, dict):
                        mod_creator = first_dev.get('display_name') or first_dev.get('username') or "Unknown Creator"
                
                mod_desc = item.get('description')
                if not mod_desc and item.get('versions') and len(item['versions']) > 0:
                    mod_desc = item['versions'][0].get('description')
                if not mod_desc:
                    mod_desc = 'No description provided.'
                
                if not Mod.query.filter_by(mod_id=mod_id).first():
                    new_mod = Mod(
                        mod_id=mod_id, title=mod_title, creator=mod_creator, 
                        description=mod_desc, downloads=item.get('download_count', 0), 
                        logo_url=item.get('logo') or "", download_link=dl_link
                    )
                    db.session.add(new_mod)
            db.session.commit()
            print("Finished saving mods!\n")
        except Exception as e:
            print(f"Error: {e}")

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '').strip()
    query = Mod.query
    if search_query:
        query = query.filter(Mod.title.ilike(f'%{search_query}%'))
    
    query = query.order_by(Mod.downloads.desc())
    mods_page = query.paginate(page=page, per_page=10, error_out=False)
    return render_template('index.html', mods_page=mods_page, search_query=search_query)

@app.route('/mod/<mod_id>')
def mod_detail(mod_id):
    mod = Mod.query.filter_by(mod_id=mod_id).first_or_404()
    is_saved = False
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if mod in user.saved_mods:
            is_saved = True
    return render_template('mod_detail.html', mod=mod, is_saved=is_saved)

@app.route('/save_mod/<int:id>')
def save_mod(id):
    if 'user_id' not in session:
        flash("You must be logged in to save mods.", "error")
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    mod = Mod.query.get_or_404(id)
    if mod not in user.saved_mods:
        user.saved_mods.append(mod)
        db.session.commit()
    return redirect(url_for('profile'))

@app.route('/unsave_mod/<int:id>')
def unsave_mod(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    mod = Mod.query.get_or_404(id)
    if mod in user.saved_mods:
        user.saved_mods.remove(mod)
        db.session.commit()
    return redirect(url_for('profile'))

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session:
        flash("You must be logged in to upload mods.", "error")
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        new_mod = Mod(
            mod_id="custom." + str(uuid.uuid4())[:8],
            title=request.form['title'],
            creator=request.form['creator'],
            description=request.form['description'],
            downloads=0
        )
        db.session.add(new_mod)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('upload.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash("Username already exists!", "error")
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash("Email is already registered!", "error")
            return redirect(url_for('register'))
            
        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, email=email, password_hash=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            return redirect(url_for('profile'))
        else:
            flash("Invalid username or password!", "error")
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/profile')
@app.route('/profile/<username>')
def profile(username=None):
    if username:
        user = User.query.filter_by(username=username).first_or_404()
        own_profile = ('user_id' in session and session['user_id'] == user.id)
    else:
        if 'user_id' not in session:
            flash("Please log in to view your profile.", "error")
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        own_profile = True
        
    return render_template('profile.html', user=user, own_profile=own_profile)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            token = str(uuid.uuid4())
            user.reset_token = token
            db.session.commit()
            reset_link = url_for('reset_password', token=token, _external=True)
            print(f"\n\n=== NEW MESSAGE ===")
            print(f"To: {user.email}")
            print(f"Click this link to reset your password: {reset_link}")
            print(f"===================\n\n")
            return "A password reset link has been sent! Check your terminal."
        return "Email not found."
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    if not user:
        return "Invalid or expired token."
        
    if request.method == 'POST':
        new_password = request.form['password']
        user.password_hash = generate_password_hash(new_password)
        user.reset_token = None
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('reset_password.html')

if __name__ == '__main__':
    app.run(debug=True)
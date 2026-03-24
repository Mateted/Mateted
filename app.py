from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import requests

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SECRET_KEY'] = 'super_secret_key_for_sessions'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

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
    if not User.query.filter_by(username="admin").first():
        test_user = User(username="admin", password="password123")
        db.session.add(test_user)
        db.session.commit()
        
    if Mod.query.count() < 10:
        try:
            print("Fetching top 500 mods from Geode...")
            geode_mods = []
            for page in range(1, 6):
                url = f"https://api.geode-sdk.org/v1/mods?per_page=100&page={page}"
                response = requests.get(url)
                if response.status_code == 200:
                    data = response.json()
                    geode_mods.extend(data.get('payload', {}).get('data', []))
            
            for item in geode_mods:
                mod_id = item.get('id', 'Unknown ID')
                mod_title = item.get('name') or item.get('title')
                
                dl_link = ""
                if item.get('versions') and isinstance(item['versions'], list) and len(item['versions']) > 0:
                    latest_version = item['versions'][0]
                    if not mod_title:
                        mod_title = latest_version.get('name') or latest_version.get('title')
                    dl_link = latest_version.get('download_link', '')
                    
                if not mod_title or mod_title == mod_id:
                    parts = mod_id.split('.')
                    mod_title = parts[-1].replace('-', ' ').title()

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
                    mod_desc = 'No description provided by the developer.'
                
                mod_downloads = item.get('download_count', 0)
                logo = item.get('logo') or ""
                
                if not Mod.query.filter_by(mod_id=mod_id).first():
                    new_mod = Mod(
                        mod_id=mod_id, title=mod_title, creator=mod_creator, 
                        description=mod_desc, downloads=mod_downloads, 
                        logo_url=logo, download_link=dl_link
                    )
                    db.session.add(new_mod)
            db.session.commit()
            print("Successfully added mods to your database!")
        except Exception as e:
            print("Could not connect to Geode:", e)

@app.route('/')
def index():
    sort_by = request.args.get('sort', 'downloads_desc')
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '').strip()
    
    query = Mod.query
    
    if search_query:
        query = query.filter(Mod.title.ilike(f'%{search_query}%'))
    
    if sort_by == 'az':
        query = query.order_by(Mod.title.asc())
    elif sort_by == 'za':
        query = query.order_by(Mod.title.desc())
    elif sort_by == 'downloads_asc':
        query = query.order_by(Mod.downloads.asc())
    else:
        query = query.order_by(Mod.downloads.desc())
        
    mods_page = query.paginate(page=page, per_page=10, error_out=False)
    return render_template('index.html', mods_page=mods_page, sort_by=sort_by, search_query=search_query)

@app.route('/mod/<mod_id>')
def mod_detail(mod_id):
    mod = Mod.query.filter_by(mod_id=mod_id).first_or_404()
    return render_template('mod_detail.html', mod=mod)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True)
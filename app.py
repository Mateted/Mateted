from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

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
    title = db.Column(db.String(100), nullable=False)
    creator = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)


with app.app_context():
    db.create_all()

    if not User.query.filter_by(username="admin").first():
        test_user = User(username="admin", password="password123")
        db.session.add(test_user)
        db.session.commit()



@app.route('/')
def index():
    all_mods = Mod.query.all()
    return render_template('index.html', mods=all_mods)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        new_mod = Mod(
            title=request.form.get('title'),
            creator=request.form.get('creator'),
            description=request.form.get('description')
        )
        db.session.add(new_mod)
        db.session.commit()
        return redirect(url_for('index'))
    
    return render_template('upload.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        entered_username = request.form.get('username')
        entered_password = request.form.get('password')
        
        user = User.query.filter_by(username=entered_username).first()
        
  
        if user and user.password == entered_password:
            return redirect(url_for('index'))
        else:
            error = "Invalid username or password. Try 'admin' and 'password123'"

    return render_template('login.html', error=error)

if __name__ == '__main__':
    app.run(debug=True)
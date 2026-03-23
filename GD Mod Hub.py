from flask import Flask, request, render_template_string

app = Flask(__name__)

LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Basic Login</title>
    <style>
        body { background-color: #121212; color: white; font-family: sans-serif; text-align: center; margin-top: 100px; }
        form { display: inline-block; background: #1A202C; padding: 20px; border-radius: 8px; border: 1px solid #00E5FF; }
        input { display: block; margin: 10px auto; padding: 8px; width: 200px; }
        button { background-color: #39FF14; border: none; padding: 10px 20px; cursor: pointer; font-weight: bold; }
    </style>
</head>
<body>
    <h2>GD Mod Hub - Test Login</h2>
    
    <form method="POST" action="/login">
        <input type="text" name="username" placeholder="Username" required>
        <input type="password" name="password" placeholder="Password" required>
        <button type="submit">Login</button>
    </form>
    
    <p style="color: red;">{{ error_message }}</p>
</body>
</html>
"""

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ""
    
    if request.method == 'POST':
        entered_username = request.form.get('username')
        entered_password = request.form.get('password')
        
        if entered_username == "admin" and entered_password == "geometry123":
            return "<h1 style='color: #39FF14; text-align: center; margin-top: 100px;'>Login Successful! Welcome to nowhere.</h1>"
        else:
            error = "Wrong username or password. Try again."
            
    return render_template_string(LOGIN_HTML, error_message=error)

if __name__ == '__main__':
    app.run(debug=True)
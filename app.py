from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
import mysql.connector
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database configuration
db_config = {
    'user': 'root',
    'password': 'Arth@F1',
    'host': 'localhost',
    'database': 'quiz_app'
}

class User(UserMixin):
    def __init__(self, id, username, has_taken_quiz):
        self.id = id
        self.username = username
        self.has_taken_quiz = has_taken_quiz

@login_manager.user_loader
def load_user(user_id):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if user:
        return User(user['id'], user['username'], user['has_taken_quiz'])
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user and check_password_hash(user['password'], password):
            login_user(User(user['id'], user['username'], user['has_taken_quiz']))
            return redirect(url_for('home'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/')
@login_required
def home():
    if current_user.has_taken_quiz:
        flash("You've already taken the quiz.")
        return redirect(url_for('logout'))
    return render_template('home.html')

@app.route('/quiz')
@login_required
def quiz():
    if current_user.has_taken_quiz:
        flash('You have already taken the quiz.')
        return redirect(url_for('home'))
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM questions")
    questions = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('quiz.html', questions=questions)

@app.route('/submit_quiz', methods=['POST'])
@login_required
def submit_quiz():
    responses = request.form.to_dict()
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    for question_id, answer in responses.items():
        cursor.execute("INSERT INTO responses (user_id, question_id, response) VALUES (%s, %s, %s)", 
                       (current_user.id, question_id, answer))
    cursor.execute("UPDATE users SET has_taken_quiz = TRUE WHERE id = %s", (current_user.id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Quiz submitted successfully.')
    return redirect(url_for('home'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)

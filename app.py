from flask import *
from decors import login_required, admin_required, single_submit
from DB import DB
from DbObject import DbObject
from datetime import datetime
from Schema import Schema
from dotenv import load_dotenv
import os 

app = Flask(__name__)
app.secret_key = 'mysecret'
load_dotenv()

db = DB(os.environ['MONGODB_URI'])
db.set_db('cyberx-2024')


user_schema = Schema({
    "username": {
        "type": str,
        "required": True
    },
    "password": {
        "type": str,
        "required": True
    },
    "is_admin": {
        "type": bool,
        "required": True
    },  
    "name":{
        "type": str,
        "required": True
    },
    "quiz" :{
        "type": bool,
        "required": True
    },
    "created_at": {
        "type": str,
        "required": True,
    }
})

answers_schema = Schema({
    "username": {
        "type": str,
        "required": True
    },
    "answers": {
        "type": list,
        "required": True
    }
})

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/login",methods=["POST", "GET"])
def login():

    # check if login is done already
    username = request.cookies.get("username")
    password = request.cookies.get("password")

    if username and password:
        return redirect("/")

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # check if username and password exists in database
        db.set_collection('code-prelims-users')

        user = db.get_object({"username": username}).compile()
        
        print("Found user as " , user)


        if user:
            # set cookie for username, password
            response = make_response(redirect('/'))
            response.set_cookie("username", username)
            response.set_cookie("password", password)
            return response 
        
        else:
            return "Invalid username or password"
            
            

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
@admin_required
def register():
    alert_message = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user_type = request.form["user_type"]
        name = request.form["name"]

        db.set_collection('code-prelims-users')
        
        user = db.get_object({"username": username}).compile() 
        if user:
            alert_message = "Username already exists"
            return render_template("register.html", alert_message=alert_message)

        user = DbObject(user_schema)
        user.add(("username", username))
        user.add(("password", password))
        user.add(("is_admin", user_type == "admin"))
        user.add(("name", name))
        user.add(("quiz", False))
        user.add(("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        db.insert(user)
        alert_message = "User registered successfully: " + str(db.get_object({"username": username}).get("username"))

    return render_template("register.html", alert_message=alert_message)


@app.route("/logout")
@login_required
def logout():
    response = make_response(redirect('/'))
    response.set_cookie("username", '', expires=0)
    response.set_cookie("password", '', expires=0)
    return response

@app.route("/users")
@admin_required
def users():
    db.set_collection('code-prelims-users')
    users = db.get_objects({})
    return render_template("users.html", users=[obj.compile() for obj in users])
 
@app.route("/start-quiz",methods=["POST"])
@login_required
def start_quiz():
    # get the user's quiz status
    user = db.get_object({"username": request.cookies.get("username")}).compile()
    if user.get("quiz", False):
        return jsonify({"message": "You have already started the quiz"})
    else:
        db.update({"username": request.cookies.get("username")},{"$set":{"quiz": True}})
        return jsonify({"message": "Quiz started successfully"})  


@app.route("/quiz", methods=["GET", "POST"])
@login_required
@single_submit
def quiz():

    # if quiz started already
    db.set_collection('code-prelims-users')
    is_quiz = db.get_object({"username": request.cookies.get('username')}).compile().get('quiz',False)

    if is_quiz :
        return jsonify({"message": "Quiz already started!.Please contact your organizer to reset the switch if you feel this is a mistake."})

    if request.method == "POST":
        # get 'answers' from post data 
        data = request.json
        answers = data['answers']
        
        # publish ansers to the database
        db.set_collection('code-prelims-submissions')
        answer = DbObject(answers_schema)
        
        answer.add(("username", request.cookies.get("username")))
        answer.add(("answers", answers))

        db.insert(answer)

        print(json.dumps(
            db.get_object({"username": request.cookies.get("username")}).compile()
            ))

        return jsonify({"message": "Quiz submitted successfully"})
        

    questions = []

    # question 1-10 are mcqs
    for i in range(1,11):
        questions.append({
            "image" : f"/static/images/{i}.png",
            "type" : "mcq",
            "question" : f"Question {i}",
            "options" : [f"Option {j}" for j in range(1,5)],
            "timeout" : 95
        })

    for i in range(11,24):
        questions.append({
            "image" : f"/static/images/{i}.png",
            "type" : "short_ans",
            "question" : f"Question {i}",
            "timeout" : 300
        })

    for i in range(24,26):
        questions.append({
            "image" : f"/static/images/{i}.png",
            "type" : "long_ans",
            "question" : f"Question {i}",
            "timeout" : 600
        })

    
    return render_template("quizv2.html",questions=questions)


@app.route("/results", methods=["GET"])
@admin_required
def results():
    db.set_collection('code-prelims-submissions')
    submissions = [x.compile() for x in db.get_objects({})]

    processed_results = []
    for submission in submissions:
        username = submission.get('username', 'Unknown')
        answers = submission.get('answers', [])

        user_result = {'username': username, 'questions': []}
        for answer in answers:
            question_number = answer.get('questionIndex', 'Unknown') + 1
            user_result['questions'].append({
                'number': question_number,
                'answer': answer.get('answer'),
                'completed': answer.get('completed'),
                'type': answer.get('type'),
                'timeSpent': answer.get('timeSpent')
            })
        processed_results.append(user_result)

    return render_template("results.html", results=processed_results)


@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    question_index = int(request.form['question_index'])
    answer = request.form['answer']
    # Process the answer
    # return redirect(url_for('results'))
    return jsonify({"question_index": question_index, "answer": answer})

# admin routes 
@app.route('/admin_f/<func>')
@admin_required

def admin_f(func):
    db.set_collection('code-prelims-users')
    if func == "rename":
        username = request.args.get('username')
        new_name = request.args.get('new_name')
        
        if username == new_name or (not username) or (not new_name):
            return jsonify({"message": "Invalid inputs"})

        else:
            db.update({"username":username}, {"$set":{"username":new_name}})
            return jsonify({"message": "Username renamed successfully"})

    elif func == "delete":
        username = request.args.get('username')

        if not username:
            return jsonify({"message": "Invalid inputs"})
        
        else:
            db.delete({"username":username})
            return jsonify({"message": "User deleted successfully"})

    elif func == 'chpass':
        username = request.args.get('username')
        new_password = request.args.get('password')

        if not username or not new_password:
            return jsonify({"message": "Invalid inputs"})
        
        else:
            db.update({"username":username}, {"$set":{"password":new_password}})
            return jsonify({"message": "Password changed successfully"})
    
    elif func == 'make_admin':
        username = request.args.get('username')
        
        if not username:
            return jsonify({"message": "Invalid inputs"})

        else:
            db.update({"username":username}, {"$set":{"is_admin":True}})
            return jsonify({"message": "User made admin successfully"})
        
    elif func == 'remove_admin':
        username = request.args.get('username')
        
        if not username:
            return jsonify({"message": "Invalid inputs"})
        
        else:
            db.update({"username":username}, {"$set":{"is_admin":False}})
            return jsonify({"message": "User removed admin successfully"})

    elif func == "regen_quiz":
        username = request.args.get("username")

        if not username:
            return jsonify({"message": "Invalid inputs"})
        
        else:
            db.update({"username": username}, {"$set":{"quiz": False}})
            db.set_collection("code-prelims-submissions")
            db.delete({"username": username})
            return jsonify({"message": "Quiz reset successfully"})

@app.route('/admin')
@admin_required
def admin():
    return render_template('admin.html')


if __name__ == "__main__":
    app.run(debug=True,host="0.0.0.0")

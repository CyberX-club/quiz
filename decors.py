from functools import wraps
from flask import request, redirect, url_for, make_response, session
from DB import DB
db = DB("mongodb+srv://cyberxadmin:cyberxpass@cyberx01.vfdin.mongodb.net/?retryWrites=true&w=majority&appName=CyberX01")
db.set_db('cyberx-2024')


# Login Required Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if username and password are set in cookies
        username = request.cookies.get("username")
        password = request.cookies.get("password")
        
        if not username or not password:
            return redirect(url_for("login"))
        
        # Check if the user exists in the database
        db.set_collection('code-prelims-users')
        user = db.get_object({"username": username, "password": password})

        if not user:
            # Clear cookies if login is invalid
            response = make_response(redirect(url_for("login")))
            response.set_cookie("username", '', expires=0)
            response.set_cookie("password", '', expires=0)
            return response

        return f(*args, **kwargs)
    return decorated_function

# Admin Required Decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Ensure the user is logged in first
        username = request.cookies.get("username")
        
        if not username:
            return redirect(url_for("login"))
        
        # Check if the user is an admin
        db.set_collection('code-prelims-users')
        user = db.get_object({"username": username})

        if not user or not user.get("is_admin", False):
            return "Access Denied: Admins Only", 403
        
        return f(*args, **kwargs)
    return decorated_function

def single_submit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        db.set_collection('code-prelims-submissions')

        # Check if the user has already submitted a code by finding it in the database
        username = request.cookies.get('username')
        if username:
            submission = db.get_object({"username": username}).compile()

            if submission:
                return "Error: You have already submitted a code", 403
            

        return f(*args, **kwargs)
    return decorated_function

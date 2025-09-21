import json
import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

DATA_FILE = "users.json"
TAPRAIN_API_KEY = "68cc259e7c4405cface28739"
TAPRAIN_API_URL = "https://taprain.com/api/templates/feed"
TARGET_OFFERS = ["Alibaba", "Opera GX", "TikTok"]  # Filter specific offers


def load_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}


def save_users(users):
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)


users = load_users()


def generate_user_offers(user_email):
    """Fetch 3 custom offers from Taprain API for the user"""
    params = {
        "api_key": TAPRAIN_API_KEY,
        "s1": user_email,
        "max": 20
    }
    try:
        response = requests.get(TAPRAIN_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        offers = data if isinstance(data, list) else data.get("offers", [])

        # Filter only target offers
        filtered_offers = [
            {
                "title": o.get("name"),
                "description": "Complete this to earn rewards",
                "link": o.get("tracking_url") or o.get("offer_url") or o.get("url")
            }
            for o in offers
            if any(keyword.lower() in o.get("name", "").lower() for keyword in TARGET_OFFERS)
        ]
        return filtered_offers[:3] if filtered_offers else []

    except Exception as e:
        print("Error fetching Taprain offers:", e)
        # fallback offers
        return [
            {"title": "Offer 1", "description": "Complete this to earn $5", "link": "#"},
            {"title": "Offer 2", "description": "Sign up to earn $3", "link": "#"},
            {"title": "Offer 3", "description": "Share to earn $2", "link": "#"}
        ]


@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('home'))
    form_type = request.args.get("form", "signup")
    return render_template('index.html', form_type=form_type)


@app.route('/signup', methods=['POST'])
def signup():
    global users
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']
    confirm = request.form['confirm']

    if password != confirm:
        flash("Passwords do not match!")
        return redirect(url_for('index', form="signup"))
    if email in users:
        flash("User already exists!")
        return redirect(url_for('index', form="signup"))

    # Generate 3 custom Taprain offers
    user_offers = generate_user_offers(email)

    users[email] = {
        "name": name,
        "email": email,
        "password": generate_password_hash(password),
        "offers": user_offers
    }
    save_users(users)
    session['user'] = users[email]
    return redirect(url_for('home'))


@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    if email not in users:
        flash("Email does not exist!")
        return redirect(url_for('index', form="login"))
    if not check_password_hash(users[email]['password'], password):
        flash("Wrong password!")
        return redirect(url_for('index', form="login"))

    session['user'] = users[email]
    return redirect(url_for('home'))


@app.route('/home')
def home():
    if 'user' not in session:
        return redirect(url_for('index'))
    return render_template('home.html', user=session['user'])


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index', form="login"))


if __name__ == '__main__':
    app.run(debug=True)

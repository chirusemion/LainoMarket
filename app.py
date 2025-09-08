from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os

# ------------------------
# Flask App Configuration
# ------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your-secret-key")  # For sessions and login

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lainomarket.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Flask-Login configuration
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ------------------------
# Models
# ------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.String(50), nullable=False)
    in_stock = db.Column(db.Boolean, default=True)

# ------------------------
# User Loader
# ------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ------------------------
# Routes
# ------------------------
@app.route("/")
def index():
    products = Product.query.filter_by(in_stock=True).all()
    return render_template("index.html", products=products)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            login_user(user)
            flash("Logged in successfully!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password", "danger")
    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    products = Product.query.all()
    return render_template("dashboard.html", products=products, user=current_user)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

# ------------------------
# Create DB and default users (if needed)
# ------------------------
@app.before_first_request
def create_tables():
    db.create_all()
    # Example: Add one admin and one farmer if they don't exist
    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin", password="admin123", is_admin=True)
        db.session.add(admin)
    if not User.query.filter_by(username="farmer1").first():
        farmer1 = User(username="farmer1", password="farmer123", is_admin=False)
        db.session.add(farmer1)
    db.session.commit()

# ------------------------
# Run Server (for local dev only)
# ------------------------
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

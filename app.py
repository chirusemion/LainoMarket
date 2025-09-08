from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config["SECRET_KEY"] = "your_secret_key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///market.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


# -------------------
# Database Models
# -------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # "admin" or "farmer"


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(50), nullable=False)  # e.g., "kg", "bundle"
    in_stock = db.Column(db.Boolean, default=True)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# -------------------
# Routes
# -------------------
@app.route("/")
def index():
    products = Product.query.all()
    return render_template("index.html", products=products)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            login_user(user)
            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))
            elif user.role == "farmer":
                return redirect(url_for("farmer_dashboard"))
        else:
            flash("Invalid username or password", "danger")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


# -------------------
# Dashboards
# -------------------
@app.route("/admin")
@login_required
def admin_dashboard():
    if current_user.role != "admin":
        return redirect(url_for("index"))
    products = Product.query.all()
    return render_template("admin_dashboard.html", products=products)


@app.route("/farmer")
@login_required
def farmer_dashboard():
    if current_user.role != "farmer":
        return redirect(url_for("index"))
    products = Product.query.all()
    return render_template("farmer_dashboard.html", products=products)


# -------------------
# Product Management
# -------------------
@app.route("/add_product", methods=["POST"])
@login_required
def add_product():
    if current_user.role not in ["admin", "farmer"]:
        return redirect(url_for("index"))

    name = request.form.get("name")
    price = request.form.get("price")
    unit = request.form.get("unit")

    product = Product(name=name, price=price, unit=unit)
    db.session.add(product)
    db.session.commit()
    return redirect(url_for("admin_dashboard" if current_user.role == "admin" else "farmer_dashboard"))


@app.route("/delete_product/<int:product_id>")
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    if current_user.role == "admin" or current_user.role == "farmer":
        db.session.delete(product)
        db.session.commit()
    return redirect(url_for("admin_dashboard" if current_user.role == "admin" else "farmer_dashboard"))


# -------------------
# Initialize DB
# -------------------
with app.app_context():
    db.create_all()
    # Pre-register admin and farmers if not already in DB
    if not User.query.filter_by(username="admin").first():
        admin_user = User(username="admin", password="admin123", role="admin")
        db.session.add(admin_user)

    farmers = [
        {"username": "farmer1", "password": "farmer123"},
        {"username": "farmer2", "password": "farmer123"},
        {"username": "farmer3", "password": "farmer123"},
        {"username": "farmer4", "password": "farmer123"},
        {"username": "farmer5", "password": "farmer123"},
    ]

    for farmer in farmers:
        if not User.query.filter_by(username=farmer["username"]).first():
            db.session.add(User(username=farmer["username"], password=farmer["password"], role="farmer"))

    db.session.commit()


# -------------------
# Run App
# -------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

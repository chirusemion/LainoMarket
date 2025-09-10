import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

# ---------------- APP SETUP ----------------
app = Flask(__name__)
app.secret_key = "your_secret_key"

# ---------------- DATABASE ----------------
DB_PATH = "/home/miola/data/market.db"
IMG_FOLDER = "/home/miola/data/images"

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = IMG_FOLDER

# Ensure images folder exists
os.makedirs(IMG_FOLDER, exist_ok=True)

db = SQLAlchemy(app)

# ---------------- MODELS ----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    weight_or_quantity = db.Column(db.String(50), nullable=False)
    image_filename = db.Column(db.String(200), nullable=False)
    in_stock = db.Column(db.Boolean, default=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey("user.id"))

# ---------------- CREATE TABLES & DEFAULT USERS ----------------
with app.app_context():
    db.create_all()

    admins = [
        {"username": "admin1", "password": "admin123"},
        {"username": "admin2", "password": "admin123"}
    ]
    for a in admins:
        if not User.query.filter_by(username=a["username"]).first():
            db.session.add(User(username=a["username"], password=a["password"], role="admin"))

    farmers = [
        {"username": "farmer1", "password": "farmer123"},
        {"username": "farmer2", "password": "farmer123"},
        {"username": "farmer3", "password": "farmer123"},
        {"username": "farmer4", "password": "farmer123"},
        {"username": "farmer5", "password": "farmer123"}
    ]
    for f in farmers:
        if not User.query.filter_by(username=f["username"]).first():
            db.session.add(User(username=f["username"], password=f["password"], role="farmer"))

    db.session.commit()

# ---------------- ROUTES ----------------

@app.route("/")
def home():
    products = Product.query.filter_by(in_stock=True).all()
    return render_template("home.html", products=products)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session["user_id"] = user.id
            session["role"] = user.role
            return redirect(url_for("dashboard"))
        else:
            session["error"] = "Invalid username or password"
            return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])

    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        price = float(request.form["price"])
        weight_or_quantity = request.form["weight_or_quantity"]
        file = request.files["image"]

        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            db.session.add(Product(
                name=name,
                description=description,
                price=price,
                weight_or_quantity=weight_or_quantity,
                image_filename=filename,
                farmer_id=user.id
            ))
            db.session.commit()
        return redirect(url_for("dashboard"))

    products = Product.query.all() if user.role == "admin" else Product.query.filter_by(farmer_id=user.id).all()
    return render_template("dashboard.html", user=user, products=products)

@app.route("/edit_product/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = User.query.get(session["user_id"])
    if user.role != "admin":
        return redirect(url_for("dashboard"))

    product = Product.query.get(product_id)
    if not product:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        product.name = request.form["name"]
        product.description = request.form["description"]
        product.price = float(request.form["price"])
        product.weight_or_quantity = request.form["weight_or_quantity"]
        file = request.files.get("image")
        if file and file.filename != "":
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            old_image = os.path.join(app.config["UPLOAD_FOLDER"], product.image_filename)
            if os.path.exists(old_image):
                os.remove(old_image)
            product.image_filename = filename
        db.session.commit()
        return redirect(url_for("dashboard"))
    return render_template("edit_product.html", product=product)

@app.route("/delete_product/<int:product_id>")
def delete_product(product_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = User.query.get(session["user_id"])
    if user.role != "admin":
        return redirect(url_for("dashboard"))

    product = Product.query.get(product_id)
    if product:
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], product.image_filename)
        if os.path.exists(image_path):
            os.remove(image_path)
        db.session.delete(product)
        db.session.commit()
    return redirect(url_for("dashboard"))

# ---------------- MAIN ----------------
if __name__ == "__main__":
    app.run(debug=True)

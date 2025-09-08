import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.utils import secure_filename

# ------------------ Flask Setup ------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'

# Absolute path for SQLite database
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'instance', 'database.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static', 'images')

# Ensure necessary folders exist
os.makedirs(os.path.join(basedir, 'instance'), exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ------------------ Database ------------------
db = SQLAlchemy(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'admin' or 'farmer'

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    weight_or_quantity = db.Column(db.String(50), nullable=True)
    image_filename = db.Column(db.String(100), nullable=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('user.id'))

# ------------------ Login Manager ------------------
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ------------------ Initialize Database & Users ------------------
with app.app_context():
    db.create_all()

    # Pre-register admin and 5 farmers if not exist
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', password='admin123', role='admin')
        db.session.add(admin)
        for i in range(1, 6):
            farmer = User(username=f'farmer{i}', password=f'farmer{i}123', role='farmer')
            db.session.add(farmer)
        db.session.commit()

# ------------------ Routes ------------------

# Home / Buyer Page
@app.route('/')
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            login_user(user)
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('farmer_dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html')

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# ------------------ Admin Dashboard ------------------
@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    products = Product.query.all()
    return render_template('admin_dashboard.html', products=products)

@app.route('/admin/delete/<int:product_id>')
@login_required
def admin_delete(product_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    product = Product.query.get(product_id)
    if product:
        db.session.delete(product)
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

# ------------------ Farmer Dashboard ------------------
@app.route('/farmer')
@login_required
def farmer_dashboard():
    if current_user.role != 'farmer':
        return redirect(url_for('index'))
    products = Product.query.filter_by(farmer_id=current_user.id).all()
    return render_template('farmer_dashboard.html', products=products)

@app.route('/farmer/add', methods=['POST'])
@login_required
def add_product():
    if current_user.role != 'farmer':
        return redirect(url_for('index'))

    name = request.form['name']
    description = request.form['description']
    price = float(request.form['price'])
    weight_or_quantity = request.form['weight_or_quantity']
    image = request.files['image']
    filename = None

    if image:
        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    product = Product(
        name=name,
        description=description,
        price=price,
        weight_or_quantity=weight_or_quantity,
        image_filename=filename,
        farmer_id=current_user.id
    )
    db.session.add(product)
    db.session.commit()
    return redirect(url_for('farmer_dashboard'))

@app.route('/farmer/delete/<int:product_id>')
@login_required
def farmer_delete(product_id):
    if current_user.role != 'farmer':
        return redirect(url_for('index'))
    product = Product.query.get(product_id)
    if product and product.farmer_id == current_user.id:
        db.session.delete(product)
        db.session.commit()
    return redirect(url_for('farmer_dashboard'))

# ------------------ Run App ------------------
if __name__ == '__main__':
    app.run(debug=True)

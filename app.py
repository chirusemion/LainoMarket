from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "supersecretkey")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lainomarket.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# ----------------- Models -----------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    role = db.Column(db.String(50))  # 'admin' or 'farmer'

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    description = db.Column(db.Text)
    price = db.Column(db.Float)
    quantity = db.Column(db.String(50))
    image = db.Column(db.String(250))
    farmer_id = db.Column(db.Integer, db.ForeignKey('user.id'))

# ----------------- User loader -----------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ----------------- Routes -----------------
@app.route('/')
def home():
    products = Product.query.all()
    return render_template('index.html', products=products)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('farmer_dashboard'))
        else:
            flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# ----------------- Admin Dashboard -----------------
@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied')
        return redirect(url_for('home'))
    products = Product.query.all()
    return render_template('admin_dashboard.html', products=products)

# ----------------- Farmer Dashboard -----------------
@app.route('/farmer')
@login_required
def farmer_dashboard():
    if current_user.role != 'farmer':
        flash('Access denied')
        return redirect(url_for('home'))
    products = Product.query.filter_by(farmer_id=current_user.id).all()
    return render_template('farmer_dashboard.html', products=products)

# ----------------- Add Product -----------------
@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if current_user.role != 'farmer':
        flash('Access denied')
        return redirect(url_for('home'))
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        quantity = request.form['quantity']
        image = request.form['image']
        product = Product(name=name, description=description, price=price,
                          quantity=quantity, image=image, farmer_id=current_user.id)
        db.session.add(product)
        db.session.commit()
        flash('Product added successfully')
        return redirect(url_for('farmer_dashboard'))
    return render_template('add_product.html')

# ----------------- Edit Product -----------------
@app.route('/edit_product/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    if current_user.role == 'farmer' and product.farmer_id != current_user.id:
        flash('Access denied')
        return redirect(url_for('home'))
    if request.method == 'POST':
        product.name = request.form['name']
        product.description = request.form['description']
        product.price = float(request.form['price'])
        product.quantity = request.form['quantity']
        product.image = request.form['image']
        db.session.commit()
        flash('Product updated successfully')
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('farmer_dashboard'))
    return render_template('edit_product.html', product=product)

# ----------------- Delete Product -----------------
@app.route('/delete_product/<int:id>')
@login_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    if current_user.role == 'farmer' and product.farmer_id != current_user.id:
        flash('Access denied')
        return redirect(url_for('home'))
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully')
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('farmer_dashboard'))

# ----------------- Initialize DB with admin + farmers -----------------
@app.before_first_request
def create_tables():
    db.create_all()
    # Check if admin/farmers exist
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', password='admin123', role='admin')
        db.session.add(admin)
    for i in range(1, 6):
        if not User.query.filter_by(username=f'farmer{i}').first():
            farmer = User(username=f'farmer{i}', password=f'farmer{i}pass', role='farmer')
            db.session.add(farmer)
    db.session.commit()

# ----------------- Run the app -----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render will provide PORT
    app.run(host="0.0.0.0", port=port, debug=True)

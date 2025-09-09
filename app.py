from flask import Flask, render_template, request, redirect, url_for, session
from models import db, User, Product
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lainomarket.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'secretkey123'
app.config['UPLOAD_FOLDER'] = 'static/images'

db.init_app(app)

# Initial setup: create tables and admin/farmers
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        # Pre-register 5 farmers
        for i in range(1, 6):
            farmer = User(username=f'farmer{i}', role='farmer')
            farmer.set_password(f'farmer{i}')
            db.session.add(farmer)
        db.session.commit()

# Homepage: show all in-stock products
@app.route('/')
def index():
    products = Product.query.filter_by(in_stock=True).all()
    return render_template('index.html', products=products)

# Login
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['role'] = user.role
            return redirect(url_for('dashboard'))
        return "Invalid credentials"
    return render_template('login.html')

# Dashboard
@app.route('/dashboard', methods=['GET','POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    user = User.query.get(session['user_id'])

    # Farmer adds a product
    if request.method == 'POST' and user.role == 'farmer':
        name = request.form['name']
        desc = request.form['description']
        price = float(request.form['price'])
        weight_or_quantity = request.form['weight_or_quantity']
        file = request.files['image']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            product = Product(name=name, description=desc, price=price,
                              weight_or_quantity=weight_or_quantity,
                              image_filename=filename,
                              farmer_id=user.id)
            db.session.add(product)
            db.session.commit()
        return redirect(url_for('dashboard'))

    # Show products
    if user.role == 'admin':
        products = Product.query.all()
    else:
        products = Product.query.filter_by(farmer_id=user.id).all()

    return render_template('dashboard.html', user=user, products=products)

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# Delete product (admin only)
@app.route('/delete_product/<int:product_id>')
def delete_product(product_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))
    user = User.query.get(session['user_id'])
    if user.role != 'admin':
        return redirect(url_for('dashboard'))
    product = Product.query.get(product_id)
    if product:
        # Delete image file if exists
        if product.image_filename:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], product.image_filename)
            if os.path.exists(image_path):
                os.remove(image_path)
        db.session.delete(product)
        db.session.commit()
    return redirect(url_for('dashboard'))

# Edit product (admin only)
@app.route('/edit_product/<int:product_id>', methods=['GET','POST'])
def edit_product(product_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))
    user = User.query.get(session['user_id'])
    if user.role != 'admin':
        return redirect(url_for('dashboard'))

    product = Product.query.get(product_id)
    if not product:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        product.name = request.form['name']
        product.description = request.form['description']
        product.price = float(request.form['price'])
        product.weight_or_quantity = request.form['weight_or_quantity']
        file = request.files.get('image')
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # Delete old image
            old_image = os.path.join(app.config['UPLOAD_FOLDER'], product.image_filename)
            if os.path.exists(old_image):
                os.remove(old_image)
            product.image_filename = filename
        db.session.commit()
        return redirect(url_for('dashboard'))

    return render_template('edit_product.html', product=product)

if __name__=='__main__':
    app.run(debug=True)

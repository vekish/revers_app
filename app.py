from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, IntegerField
from wtforms.validators import DataRequired
import pdfkit
import base64
import os
from io import BytesIO
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///revers.db'
db = SQLAlchemy(app)

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(10), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    pib = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    division = db.Column(db.String(100), nullable=False)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

class EmployeeForm(FlaskForm):
    code = SelectField('Šifra zaposlenog', validators=[DataRequired()], choices=[('', 'Odaberite šifru')])
    name = StringField('Ime i prezime', render_kw={'readonly': True})
    email = StringField('Email', render_kw={'readonly': True})
    submit = SubmitField('Submit')

class CustomerForm(FlaskForm):
    code = SelectField('Šifra kupca', validators=[DataRequired()], choices=[('', 'Odaberite šifru')])
    name = StringField('Naziv kupca', render_kw={'readonly': True})
    pib = StringField('PIB', render_kw={'readonly': True})
    email = StringField('Email', render_kw={'readonly': True})
    division = StringField('Divizija', render_kw={'readonly': True})
    submit = SubmitField('Submit')

class ItemForm(FlaskForm):
    item = SelectField('Artikal', validators=[DataRequired()], choices=[])
    quantity = SelectField('Količina', choices=[(str(i), str(i)) for i in range(1, 11)])
    submit = SubmitField('Dodaj Artikal')

@app.route('/', methods=['GET', 'POST'])
def index():
    print("Ruta / je pozvana")
    employee_form = EmployeeForm()
    customer_form = CustomerForm()
    item_form = ItemForm()

    # Populate dropdowns
    employee_form.code.choices = [('', 'Odaberite šifru')]
    employee_form.code.choices += [(e.code, e.code) for e in Employee.query.all()]

    customer_form.code.choices = [('', 'Odaberite šifru')]
    customer_form.code.choices += [(c.code, c.code) for c in Customer.query.all()]

    item_form.item.choices = [(i.code, i.name) for i in Item.query.all()]

    if 'selected_items' not in session:
        session['selected_items'] = []

    if request.method == 'POST':
        # Ručno dodavanje podataka u sesiju pre dodavanja artikla
        session['employee_code'] = employee_form.code.data = request.form.get('employee_code', session.get('employee_code', ''))
        session['employee_name'] = employee_form.name.data = request.form.get('employee_name', session.get('employee_name', ''))
        session['employee_email'] = employee_form.email.data = request.form.get('employee_email', session.get('employee_email', ''))

        session['customer_code'] = customer_form.code.data = request.form.get('customer_code', session.get('customer_code', ''))
        session['customer_name'] = customer_form.name.data = request.form.get('customer_name', session.get('customer_name', ''))
        session['customer_pib'] = customer_form.pib.data = request.form.get('customer_pib', session.get('customer_pib', ''))
        session['customer_email'] = customer_form.email.data = request.form.get('customer_email', session.get('customer_email', ''))
        session['customer_division'] = customer_form.division.data = request.form.get('customer_division', session.get('customer_division', ''))

        session['date'] = request.form.get('date', session.get('date', ''))
        
        session.modified = True

        if 'add_item' in request.form:
            item_code = request.form['item']
            quantity = request.form['quantity']
            item = Item.query.filter_by(code=item_code).first()
            session['selected_items'].append({'code': item_code, 'name': item.name, 'quantity': quantity})
            session.modified = True

    selected_items = session['selected_items']

    # Popunjavanje formi podacima iz sesije
    if 'employee_code' in session:
        employee_form.code.data = session['employee_code']
        employee_form.name.data = session['employee_name']
        employee_form.email.data = session['employee_email']
    if 'customer_code' in session:
        customer_form.code.data = session['customer_code']
        customer_form.name.data = session['customer_name']
        customer_form.pib.data = session['customer_pib']
        customer_form.email.data = session['customer_email']
        customer_form.division.data = session['customer_division']

    return render_template('index.html', employee_form=employee_form, customer_form=customer_form, item_form=item_form, selected_items=selected_items)

@app.route('/get_employee/<code>')
def get_employee(code):
    print(f"Ruta /get_employee/{code} je pozvana")
    employee = Employee.query.filter_by(code=code).first()
    if employee:
        print(f"Podaci za zaposlenog {code}: {employee.name}, {employee.email}")
        return jsonify(name=employee.name, email=employee.email)
    return jsonify(name='', email='')

@app.route('/get_customer/<code>')
def get_customer(code):
    print(f"Ruta /get_customer/{code} je pozvana")
    customer = Customer.query.filter_by(code=code).first()
    if customer:
        print(f"Podaci za kupca {code}: {customer.name}, {customer.pib}, {customer.email}, {customer.division}")
        return jsonify(name=customer.name, pib=customer.pib, email=customer.email, division=customer.division)
    return jsonify(name='', pib='', email='', division='')

@app.route('/get_employees')
def get_employees():
    print("Ruta /get_employees je pozvana")
    employees = Employee.query.all()
    employees_dict = {employee.code: employee.name for employee in employees}
    print("GET /get_employees: ", employees_dict)
    return jsonify(employees_dict)

@app.route('/get_customers')
def get_customers():
    print("Ruta /get_customers je pozvana")
    customers = Customer.query.all()
    customers_dict = {customer.code: customer.name for customer in customers}
    print("GET /get_customers: ", customers_dict)
    return jsonify(customers_dict)

@app.route('/clear_session')
def clear_session():
    print("Ruta /clear_session je pozvana")
    session.pop('selected_items', None)
    session.pop('employee_code', None)
    session.pop('employee_name', None)
    session.pop('employee_email', None)
    session.pop('customer_code', None)
    session.pop('customer_name', None)
    session.pop('customer_pib', None)
    session.pop('customer_email', None)
    session.pop('customer_division', None)
    session.pop('signature_path', None)
    session.pop('date', None)
    return redirect(url_for('index'))

@app.route('/save_signature', methods=['POST'])
def save_signature():
    print("Ruta /save_signature je pozvana")
    signature = request.form['signed']
    signature_data = signature.split(",")[1]
    signature_bytes = base64.b64decode(signature_data)

    # Sačuvaj potpis kao fajl
    signature_filename = f"signature_{uuid.uuid4().hex}.png"
    signature_path = os.path.join("signatures", signature_filename)
    with open(signature_path, "wb") as f:
        f.write(signature_bytes)

    session['signature_path'] = signature_path
    session.modified = True
    return jsonify({"message": "Potpis je uspešno sačuvan"})

@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    print("Ruta /generate_pdf je pozvana")

    # Prikupljanje podataka iz forme
    date = request.form.get('date')  # Ovde se preuzima datum iz forme
    session['date'] = date  # Čuvanje datuma u sesiji

    employee_data = {
        'code': request.form.get('employee_code', ''),
        'name': request.form.get('employee_name', ''),
        'email': request.form.get('employee_email', '')
    }
    customer_data = {
        'code': request.form.get('customer_code', ''),
        'name': request.form.get('customer_name', ''),
        'pib': request.form.get('customer_pib', ''),
        'email': request.form.get('customer_email', ''),
        'division': request.form.get('customer_division', '')
    }
    selected_items = session.get('selected_items', [])
    signature_path = session.get('signature_path', '')
    date = session.get('date', '')

    # Log the data to ensure it is correctly set
    print(f"Employee Data: {employee_data}")
    print(f"Customer Data: {customer_data}")
    print(f"Selected Items: {selected_items}")
    print(f"Signature Path: {signature_path}")
    print(f"Date: {date}")
    print(f"Date in generate_pdf: {date}")

    signature_base64 = ''
    if signature_path and os.path.exists(signature_path):
        with open(signature_path, "rb") as sig_file:
            signature_base64 = base64.b64encode(sig_file.read()).decode('utf-8')

    rendered = render_template('pdf_template.html', 
                               employee=employee_data, 
                               customer=customer_data, 
                               items=selected_items, 
                               signature_base64=signature_base64,
                               date=date)

    # Log the rendered HTML
    print("Rendered HTML:")
    print(rendered)
    
    try:
        pdf = pdfkit.from_string(rendered, False)
        print("PDF successfully generated.")
        
        response = send_file(
            BytesIO(pdf),
            as_attachment=True,
            download_name='revers.pdf',
            mimetype='application/pdf'
        )
        return response
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return jsonify({"error": "Failed to generate PDF"}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        # Test podaci
        if not Employee.query.first():
            employees = [
                Employee(name='Marko Marković', code='E001', email='marko.markovic@example.com'),
                Employee(name='Janko Janković', code='E002', email='janko.jankovic@example.com'),
                Employee(name='Vera Šercel', code='E003', email='vekish@example.com'),
            ]
            db.session.bulk_save_objects(employees)

        if not Customer.query.first():
            customers = [
                Customer(code='C001', name='ABC d.o.o.', pib='123456789', email='kontakt@abc.rs', division='Prodaja'),
                Customer(code='C002', name='XYZ d.o.o.', pib='987654321', email='info@xyz.rs', division='Logistika'),
                Customer(code='C003', name='DEF d.o.o.', pib='111222333', email='info@def.rs', division='Digital'),
            ]
            db.session.bulk_save_objects(customers)

        if not Item.query.first():
            items = [
                Item(code='I001', name='Šraf 6x50', quantity=10),
                Item(code='I002', name='Navrtka M6', quantity=20)
            ]
            db.session.bulk_save_objects(items)

        db.session.commit()

    if not os.path.exists("signatures"):
        os.makedirs("signatures")

    app.run(debug=True, host='0.0.0.0', port=5001)

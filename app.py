from datetime import date, timedelta, datetime
from sqlalchemy.exc import IntegrityError
from flask import Flask, render_template, request, url_for, redirect, flash, abort
from flask_login import LoginManager, login_required, current_user, logout_user, login_user
from models import db, User, Doctor, Department, Slot, Appointment, Treatment

# Initializaton
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'hospitalsystem'
db.init_app(app)

# login manager setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

## Routes

######################################################################
#                            !Auth Routes          
######################################################################

# REGISTER 
@app.route('/', methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for(f'{current_user.role}_dashboard'))

    if request.method == "POST":
        name = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        phone = (request.form.get("phone") or "").strip() or None
        password = request.form.get("pass") or ""
        cpass = request.form.get("cpass") or ""

        # Validation
        if not name or not email or not password:
            flash("Name, email and password required!", "warning")
            return redirect(url_for("register"))
        if password != cpass:
            flash("Passwords do not match!", "warning")
            return redirect(url_for("register"))
        if User.query.filter_by(email=email).first():
            flash("Email already registered!", "warning")
            return redirect(url_for("register"))

        # New Patient
        patient = User(name=name, email=email, phone=phone)
        patient.set_password(password)
        db.session.add(patient)
        db.session.commit()
        flash("Registration successful. Please log in!", "success")
        return redirect(url_for("login"))
    
    return render_template('auth/register.html')


# LOGIN
@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("pass") or ""
        role = request.form.get("role") or ""
        user = User.query.filter_by(email=email).first()

        if not (user and password):
            flash("Invalid email or password!", "danger")
            return redirect(url_for("login"))
        
        if not user.check_password(password):
            flash("Invalid email or password!", "danger")
            return redirect(url_for("login"))
            
        if user.role != role:
            flash(f"You are not registered with {role} role!", "warning")
            return redirect(url_for("login"))
        if user.is_blocked:
            flash("Account is blocked. Please contact admin!", "danger")
            return redirect(url_for("login"))
        
        login_user(user)
        flash("Logged in successfully!", "success")

        # redirecting based on role 
        if user.role == "patient": 
            return redirect(url_for("patient_dashboard"))
        elif user.role == "doctor":
            return redirect(url_for("doctor_dashboard"))
        elif user.role == "admin":
            return redirect(url_for("admin_dashboard"))

    return render_template('auth/login.html')

# LOGOUT
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out!", "info")
    return redirect(url_for("login"))


###################################################################
#                            !Patient Routes          
###################################################################

# PATIENT DASHBOARD
@app.route('/patient_dashboard')
@login_required
def patient_dashboard():
    departments = Department.query.all()
    appointments = (
        Appointment.query
        .join(Slot) 
        .filter(Appointment.patient_id == current_user.id,
                Slot.date >= date.today())
        .order_by(Slot.date.asc(), Slot.time.desc()) 
        .all())
    
    return render_template('patient/patient_dash.html', departments=departments, appointments=appointments)


# PATIENT SEARCH
@app.route('/patient_search')
@login_required
def patient_search():
    q = request.args.get('q')
    search_term = f"%{q}%"
    doctors = (Doctor.query
               .join(User)
               .join(Department)
               .filter((User.name.ilike(search_term)) | 
                       (Department.name.ilike(search_term)))
               .all())

    return render_template('patient/search_results.html', doctors=doctors, q=q)

# DEPARTMENT DETAILS
@app.route('/department_details/<int:dept_id>')
@login_required
def department_details(dept_id):
    dept = Department.query.get_or_404(dept_id)
    return render_template('patient/dept_details.html', dept=dept)


# CANCEL APPOINTMENT  (patient/doctor)
@app.route('/cancel_appointment/<int:id>', methods=['POST'])
@login_required
def cancel_appointment(id):
    ap = Appointment.query.get_or_404(id)
    if (ap.patient_id != current_user.id) and (current_user.role not in ['admin', 'doctor']):
        abort(403)
    ap.status = 'cancelled'
    db.session.commit()
    flash('Appointment cancelled', 'success')
    return redirect(request.referrer)

# DOCTOR DETAILS
@app.route('/doctor_details/<int:doct_id>')
@login_required
def doctor_details(doct_id):
    doctor = Doctor.query.get_or_404(doct_id)
    return render_template('patient/doctor_details.html', doctor=doctor)


# DOCTOR AVAILABILITY & SLOT BOOKING
@app.route('/check_availability/<int:doctor_id>', methods=['GET', 'POST'])
@login_required
def check_availability(doctor_id):
    if current_user.role != 'patient':
        abort(403)
        
    doctor = Doctor.query.get_or_404(doctor_id)

    if request.method == 'POST':
        slot_id = request.form.get('slot_id')
        slot = Slot.query.get(slot_id)
        if not slot:
            flash("Slot not found!", "danger")
            return redirect(url_for('check_availability', doctor_id=doctor_id))
        
        existing_booking = (Appointment.query
                            .join(Slot)
                            .filter(Appointment.patient_id == current_user.id,
                                    Appointment.status == 'booked',
                                    Slot.date == slot.date,
                                    Slot.time == slot.time)
                            .first())

        if existing_booking:
            flash(f"You already have a booking on {slot.date} in the {slot.time}!", "warning")
            return redirect(url_for('check_availability', doctor_id=doctor_id))

        if slot.appointments:
            last_appt = slot.appointments[-1]
            if last_appt.status == 'booked':
                flash("Someone just booked this slot!", "danger")
                return redirect(url_for('check_availability', doctor_id=doctor_id))
        
        
        # New Appointment
        new_appointment = Appointment(
            patient_id=current_user.id,
            doctor_id=doctor_id,
            slot_id=slot.id,
            status='booked'
        )
        
        db.session.add(new_appointment)
        db.session.commit()
        
        flash("Appointment booked successfully!", "success")
        return redirect(url_for('patient_dashboard'))

    today = date.today()
    dates = [today + timedelta(days=i) for i in range(7)]

    # existing slots
    slots = Slot.query.filter(
        Slot.doctor_id == doctor_id, 
        Slot.date >= today,
        Slot.date <= dates[-1]
    ).all()

    # slot map
    slot_map = {}

    for s in slots:
        status = 'NotAvailable'
        if s.appointments:
            apt = s.appointments[-1] 
            if apt.patient_id == current_user.id:
                if apt.status == 'cancelled':
                    status = 'CANCELLED'
                elif apt.status == 'completed':
                    status = 'COMPLETED'
                elif apt.status == 'booked':
                    status = 'BOOKED'
            else:
                if apt.status == 'cancelled':
                    status = 'OPEN'
                else:
                    status = 'NotAvailable' 
        else:
            status = 'OPEN'
        
        slot_map[(s.date, s.time)] = {'status': status, 'id': s.id}
            
    return render_template('patient/doctor_availability.html', 
                           doctor=doctor, 
                           dates=dates, 
                           slot_map=slot_map)


# PATIENT HISTORY
@app.route('/history/<int:id>')
@login_required
def history(id):
    if current_user.role != 'admin' and current_user.id != id:
        abort(403)

    patient = User.query.get_or_404(id)

    appointments = (Appointment.query
                    .join(Slot)
                    .filter(Appointment.patient_id == patient.id,
                            Appointment.status == 'completed')
                    .order_by(Slot.date.desc(), Slot.time.desc())
                    .all())
    
    return render_template('patient/history.html', appointments=appointments, patient=patient)


# PATIENT : EDIT PROFILE
@app.route('/edit_profile/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_profile(id):
    if current_user.role != 'admin' and current_user.id != id:
        abort(403)

    patient = User.query.get_or_404(id)

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        new_password = request.form.get('new_password') 

        # Checking if email id already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and existing_user.id != patient.id:
            flash("Email already in use by another account!", "warning")
            return redirect(url_for('edit_profile', id=patient.id))

        # Updating 
        patient.name = name
        patient.email = email
        patient.phone = phone

        if new_password and new_password.strip():
            patient.set_password(new_password)

        db.session.commit()
        flash("Profile updated successfully!", "success")
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'patient':
            return redirect(url_for('patient_dashboard'))

    return render_template('patient/edit_profile.html', patient=patient)



#############################################################################
#                            !Doctor Routes          
#############################################################################

# DOCTOR DASHBOARD
@app.route('/doctor_dashboard')
@login_required
def doctor_dashboard():
    appointments = (
        Appointment.query
        .join(Slot) 
        .filter(Appointment.doctor_id == current_user.id,
                Appointment.status == "booked",
                Slot.date >= date.today())
        .order_by(Slot.date.asc(), Slot.time.desc())
        .all())
    
    treatments = (
        Treatment.query
        .join(Appointment) 
        .filter(Appointment.doctor_id == current_user.id,
                Appointment.status == "completed")
        .order_by(Treatment.created_at.desc())
        .all())
    return render_template('doctor/doctor_dash.html', appointments=appointments, treatments=treatments)


# MARK APPOINTMENT
@app.route('/mark_appointment/<int:id>', methods=['POST'])
@login_required
def mark_appointment(id):
    ap = Appointment.query.get_or_404(id)
    if (ap.doctor_id != current_user.id):
        abort(403)
    ap.status = 'completed'
    db.session.commit()
    return redirect(request.referrer)


# PATIENT HISTORY
@app.route('/patient_history/<int:id>')
@login_required
def patient_history(id):
    patient = User.query.get_or_404(id)
    treatments = (
        Treatment.query
        .join(Appointment) 
        .filter(Appointment.doctor_id == current_user.id,
                Appointment.patient_id == id,
                Appointment.status == "completed")
        .order_by(Treatment.created_at.desc())
        .all())
    return render_template('doctor/patient_history.html', treatments=treatments, patient=patient)


# ADD TREATMENT DETAILS
@app.route('/add_treatment_details/<int:id>', methods=['GET', 'POST'])
@login_required
def add_treatment_details(id):
    appointment = Appointment.query.get_or_404(id)

    if appointment.doctor_id != current_user.id:
        abort(403)

    if appointment.slot.date != date.today():
        flash('You cannot add Treatment details of future appointments!', 'danger')
        return redirect(url_for('doctor_dashboard'))

    if request.method == 'POST':
        visit_type = request.form.get('visit')
        tests = request.form.get('test')
        diagnosis = request.form.get('diagnosis')
        medicines = request.form.get('medicines')
        prescription = request.form.get('prescription')

        # New Treatment
        treatment = Treatment(
            appointment_id=appointment.id,
            visit_type=visit_type,
            tests_done=tests,
            diagnosis=diagnosis,
            medicines=medicines,
            prescription=prescription
        )

        db.session.add(treatment)
        db.session.commit()
        
        flash('Treatment details added successfully!', 'success')
        return redirect(url_for('doctor_dashboard'))

    return render_template('doctor/treatment_form.html', appointment=appointment)


# UPDATE AVAILABILITY (doctor/admin)
@app.route('/update_availability/<int:user_id>', methods=['GET', 'POST'])
@login_required
def update_availability(user_id):
    doctor = Doctor.query.get_or_404(user_id)

    # Authorization Check
    if current_user.role not in ['admin', 'doctor']:
        abort(403)
    if current_user.role == 'doctor' and current_user.id != user_id:
        abort(403)

    if request.method == 'POST':
        date_str = request.form.get('date') 
        time_slot = request.form.get('time') 
        
        slot_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        # Validation
        if slot_date < date.today():
            flash("You cannot add availability for past dates!", "warning")
            return redirect(url_for('update_availability', user_id=user_id))
        
        if slot_date >= (date.today() + timedelta(days=7)):
            flash("You can only add availability for upcoming 7 days!", "warning")
            return redirect(url_for('update_availability', user_id=user_id))

        try:
            new_slot = Slot(doctor_id=user_id, date=slot_date, time=time_slot)
            db.session.add(new_slot)
            db.session.commit()
            flash("Slot added successfully!", "success")
        except IntegrityError:
            db.session.rollback()
            flash("You have already added this slot!", "danger")
        
        return redirect(url_for('update_availability', user_id=user_id))

    # Existing slots
    slots = Slot.query.filter(
        Slot.doctor_id == user_id, 
        Slot.date >= date.today()
    ).order_by(Slot.date).all()
    
    return render_template('doctor/update_availability.html', slots=slots, today=date.today(), doctor=doctor)


# DELETE SLOT
@app.route('/delete_slot/<int:id>', methods=['POST'])
@login_required
def delete_slot(id):
    slot = Slot.query.get_or_404(id)

    if current_user.role != 'admin' and current_user.id != slot.doctor_id:
        abort(403)

    if slot.appointments and slot.appointments[-1].status != 'cancelled':
        flash("Cannot delete this slot because it is booked!", "danger")
    else:
        db.session.delete(slot)
        db.session.commit()
        flash("Slot removed successfully", "success")

    return redirect(url_for('update_availability', user_id=slot.doctor_id))



#####################################################################################
#                            !Admin Routes          
#####################################################################################

# ADMIN DASHBOARD
@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        abort(403)

    total_doctors = Doctor.query.count()
    total_patients = User.query.filter_by(role='patient').count()
    total_treatments = Treatment.query.count()

    # Doctor search
    d_query = request.args.get('d')
    doc_base = Doctor.query.join(User).join(Department) 
    if d_query:
        search_term = f"%{d_query}%"
        doctors = doc_base.filter(
            (User.name.ilike(search_term)) | 
            (Department.name.ilike(search_term))
        ).all()
    else:
        doctors = doc_base.all()

    # Patient Search
    p_query = request.args.get('p')
    pat_base = User.query.filter_by(role='patient')
    if p_query:
        search_term = f"%{p_query}%"
        patients = pat_base.filter(
            (User.name.ilike(search_term)) | 
            (User.email.ilike(search_term)) |
            (User.phone.ilike(search_term))
        ).all()
    else:
        patients = pat_base.all()

    appointments = (Appointment.query
                    .join(Slot)
                    .filter(Slot.date >= date.today())
                    .order_by(Slot.date.asc(), Slot.time.desc())
                    .all())
    
    all_appointments = (Appointment.query
                    .join(Slot)
                    .filter(Slot.date < date.today())
                    .order_by(Slot.date.asc(), Slot.time.desc())
                    .all())

    return render_template('admin/admin_dash.html', 
                           doctors=doctors, 
                           patients=patients, 
                           appointments=appointments,
                           all_appointments=all_appointments,
                           total_doctors=total_doctors,
                           total_patients=total_patients,
                           total_treatments=total_treatments)


# ADD NEW DOCTOR
@app.route('/add_doctor', methods=['GET', 'POST'])
@login_required
def add_doctor():
    if current_user.role != 'admin':
        abort(403)

    departments = Department.query.all()

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        dept_id = request.form.get('dept_id')
        description = request.form.get('description')

        # Validation
        if User.query.filter_by(email=email).first():
            flash("Email already registered!", "warning")
            return redirect(url_for('add_doctor'))

        # New Doctor (Login Details)
        new_user = User(
            name=name, 
            email=email, 
            phone=phone, 
            role='doctor'
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        # New Doctor Entry (Profile Details)
        new_doctor = Doctor(
            user_id=new_user.id,
            dept_id=dept_id,
            description=description
        )
        
        db.session.add(new_doctor)
        db.session.commit()

        flash(f"{name} added successfully!", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/add_doctor.html', departments=departments)


# BLOCK/UNBLOCK Patient and Doctors
@app.route('/toggle_block/<int:user_id>')
@login_required
def toggle_block(user_id):
    if current_user.role != 'admin':
        abort(403)

    user = User.query.get_or_404(user_id)
    
    user.is_blocked = not user.is_blocked
    
    db.session.commit()
    
    status = "Blocked" if user.is_blocked else "Unblocked"
    flash(f"{user.name} has been {status}!", "success")
    
    return redirect(url_for('admin_dashboard'))


# ADD DEPARTMENT
@app.route('/add_department', methods=['GET', 'POST'])
@login_required
def add_department():
    if current_user.role != 'admin':
        abort(403)

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')

        if Department.query.filter_by(name=name).first():
            flash(f"Department '{name}' already exists!", "warning")
            return redirect(url_for('add_department'))

        # New Department
        new_dept = Department(name=name, description=description)
        db.session.add(new_dept)
        db.session.commit()

        flash(f"Department '{name}' added successfully!", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/add_department.html')


# Update Doctor's Profile
@app.route('/edit_doctor/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_doctor(user_id):
    if current_user.role != 'admin':
        abort(403)

    doctor = Doctor.query.get_or_404(user_id)
    departments = Department.query.all()

    if request.method == 'POST':
        doctor.user.name = request.form.get('name')
        doctor.dept_id = request.form.get('dept_id')
        doctor.description = request.form.get('description')

        db.session.commit()
        
        flash(f"{doctor.user.name}'s profile updated successfully!", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/edit_doctor.html', doctor=doctor, departments=departments)


# DELETE USER
@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        abort(403)

    user = User.query.get_or_404(user_id)
    name = user.name
    
    db.session.delete(user)
    db.session.commit()
    
    flash(f"User '{name}' and all associated data have been deleted.", "success")
    return redirect(url_for('admin_dashboard'))


# run
if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    # Creating a Admin if not exist 
        if not User.query.filter_by(role='admin').first():
            new_admin = User(
                name='Mr. Admin',
                email='admin@hms.com',
                role='admin',
            )
            new_admin.set_password('admin123')
            db.session.add(new_admin)
            db.session.commit()
            print('Admin user created!!')

    # Creating some default Departments
        if not Department.query.first():
            depts = [
                Department(name='General', description='General Physician'),
                Department(name='Cardiology', description='Heart Specialist'),
                Department(name='Dermatology', description='Skin Specialist'),
                Department(name='Neurology', description='Brain Specialist')
            ]
            db.session.add_all(depts)
            db.session.commit()
            print("Default Departments Created!!")

    app.run(debug=True)
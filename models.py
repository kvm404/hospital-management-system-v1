from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# USERS
class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=True)
    role = db.Column(db.String(30), default="patient", nullable=False)  # 'patient','doctor','admin'
    password_hash = db.Column(db.String(255), nullable=False)
    is_blocked = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=True)

    # relationships
    doctor_profile = db.relationship("Doctor", back_populates="user", uselist=False, cascade="all, delete-orphan")
    appointments = db.relationship("Appointment", back_populates="patient", cascade="all, delete-orphan")

    # helpers 
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# DEPARTMENTS / SPECIALIZATIONS
class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=False)

    # relationships
    doctors = db.relationship("Doctor", back_populates="department", cascade="all, delete-orphan")

# DOCTORS
class Doctor(db.Model):
    __tablename__ = "doctors"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    dept_id = db.Column(db.Integer, db.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    description = db.Column(db.Text, nullable=False)

    # relationships
    user = db.relationship("User", back_populates="doctor_profile")
    department = db.relationship("Department", back_populates="doctors")
    slots = db.relationship("Slot", back_populates="doctor", cascade="all, delete-orphan")
    appointments = db.relationship("Appointment", back_populates="doctor", cascade="all, delete-orphan")


# SLOTS
class Slot(db.Model):
    __tablename__ = "slots"

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.user_id", ondelete="CASCADE"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(20), nullable=False) # morning: 8am - 12am, evening: 4pm - 9pm
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    # relationships
    doctor = db.relationship("Doctor", back_populates="slots")
    appointments = db.relationship("Appointment", back_populates="slot", cascade="all, delete-orphan")

    __table_args__ = (
        # preventing identical slots for same doctor/date/period
        db.UniqueConstraint("doctor_id", "date", "time", name="unique_slot"),
    )


# Appointments
class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.user_id", ondelete="CASCADE"), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey("slots.id", ondelete="CASCADE"), nullable=False)
    status = db.Column(db.String(20), default="booked", nullable=False)  # booked, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    # relationships
    patient = db.relationship("User", back_populates="appointments")
    doctor = db.relationship("Doctor", back_populates="appointments")
    slot = db.relationship("Slot", back_populates="appointments")
    treatment = db.relationship("Treatment", back_populates="appointment", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        # preventing same patient booking same slot twice
        db.UniqueConstraint("patient_id", "slot_id", name="uq_patient_slot"),
    )


# TREATMENTS
class Treatment(db.Model):
    __tablename__ = "treatments"

    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False)
    visit_type = db.Column(db.String(50))
    tests_done = db.Column(db.Text)
    diagnosis = db.Column(db.Text)
    prescription = db.Column(db.Text)
    medicines = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    # relationships
    appointment = db.relationship("Appointment", back_populates="treatment")
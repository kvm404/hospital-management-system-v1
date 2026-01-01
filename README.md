# Hospital Management System (HMS)

Welcome to the **Hospital Management System**! This is a lightweight web application designed to streamline hospital operations. It helps Admins manage staff, Doctors manage their schedules, and Patients book appointments easily—all in one place.

---

## Key Features

### 1. Admin (The Superuser)
* **Dashboard:** View live statistics (Total Doctors, Patients, Treatments).
* **Manage Doctors:** Add new doctors, edit profiles, and schedule their availability.
* **Manage Departments:** Dynamically add new hospital departments.
* **User Management:** Search for users and **Block/Unblock** access.
* **Appointments:** View a master log of all upcoming and past appointments.

### 2. Doctor
* **Smart Dashboard:** View upcoming appointments and assigned patients.
* **Availability Manager:** Set weekly availability using a 7-day interactive grid.
* **Consultation:** Enter diagnosis, prescriptions, and medicines for patients.
* **History Access:** View medical history of treated patients.

### 3. Patient
* **Easy Booking:** Search for doctors by **Name** or **Department** and book slots.
* **Real-time Availability:** See exactly when a doctor is free (Green) or Booked (Red).
* **Medical History:** View past treatments, prescriptions, and test results.
* **Profile Management:** Update personal details.

---

## Tech Stack

* **Backend:** Python (Flask)
* **Database:** SQLite (SQLAlchemy ORM)
* **Frontend:** HTML5, CSS3, Bootstrap 5 (Jinja2 Templating)
* **Authentication:** Flask-Login (Secure Password Hashing)

---

## How to Run

You don't need to manually set up the database. The application is designed to **auto-configure** itself on the first run!

**1. Clone the project**
```bash
git clone https://github.com/24f2005147/hospital-management-system-v1.git
cd hospital-management-system
````

**2. Install Dependencies**

```bash
pip install -r requirements.txt
```

**3. Run the Application**

```bash
python app.py
```

**4. Open in Browser**
Go to: `http://127.0.0.1:5000`

> **Note:** When you run the app for the first time, it will automatically create the `data.db` file, seed the **Admin** account.

-----

##  Login Credentials (Demo)

Use these credentials to access the Admin panel immediately:

  * **Role:** Admin
  * **Email:** `admin@hms.com`
  * **Password:** `admin123`

*(You can create new Patient accounts via the Register page. Doctors must be added by the Admin.)*

-----

##  Project Structure

```text
/hms-project
│
│
├── static/
│   └── style.css          
│
├── templates/             
│   ├── base.html           
│   ├── admin/  
│   │    ├── admin_dash.html
│   │    ├── add_doctor.html
│   │    ├── edit_doctor.html
│   │    └── add_department.html
│   │
│   ├── doctor/            
│   │     ├── doctor_dash.html
│   │     ├── patient_history.html
│   │     ├── treatment_form.html
│   │     └── update_availability.html
│   │
│   ├── patient/            
│   │     ├── patient_dash.html
│   │     ├── doctor_availability.html
│   │     ├── dept_details.html
│   │     ├── doctor_details.html
│   │     ├── edit_profile.html
│   │     ├── history.html
│   │     └── search_results.html
│   │
│   └── auth/               
│        ├── login.html
│        └── register.html
│
├── app.py                  
├── requirements.txt                
├── README.md                
└── models.py            
```

-----

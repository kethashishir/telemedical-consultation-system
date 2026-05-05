import os
from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-this-secret-key")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "teleuser"),
    "password": os.getenv("DB_PASSWORD", "telepass123"),
    "database": os.getenv("DB_NAME", "telemedical_db"),
}


def get_db_connection():
    """Create a new MySQL connection."""
    return mysql.connector.connect(**DB_CONFIG)


def fetch_all(sql, params=None):
    params = params or ()
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    return rows


def fetch_one(sql, params=None):
    params = params or ()
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute(sql, params)
    row = cursor.fetchone()
    cursor.close()
    connection.close()
    return row


def execute_write(sql, params=None):
    params = params or ()
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(sql, params)
    connection.commit()
    last_id = cursor.lastrowid
    cursor.close()
    connection.close()
    return last_id


@app.errorhandler(Error)
def handle_mysql_error(error):
    return (
        render_template(
            "error.html",
            title="Database Error",
            message="A MySQL database error occurred.",
            detail=str(error),
        ),
        500,
    )


@app.route("/")
def dashboard():
    counts = {
        "patients": fetch_one("SELECT COUNT(*) AS total FROM patients")["total"],
        "doctors": fetch_one("SELECT COUNT(*) AS total FROM doctors")["total"],
        "appointments": fetch_one("SELECT COUNT(*) AS total FROM appointments")["total"],
        "records": fetch_one("SELECT COUNT(*) AS total FROM medical_records")["total"],
    }

    recent_appointments = fetch_all(
        """
        SELECT
            a.appointment_id,
            CONCAT(p.first_name, ' ', p.last_name) AS patient_name,
            d.full_name AS doctor_name,
            d.specialization,
            a.appointment_date,
            TIME_FORMAT(a.appointment_time, '%h:%i %p') AS appointment_time,
            a.consultation_type,
            a.status
        FROM appointments a
        JOIN patients p ON a.patient_id = p.patient_id
        JOIN doctors d ON a.doctor_id = d.doctor_id
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
        LIMIT 8
        """
    )
    return render_template(
        "dashboard.html",
        title="Dashboard",
        counts=counts,
        recent_appointments=recent_appointments,
    )


@app.route("/patients", methods=["GET", "POST"])
def patients():
    if request.method == "POST":
        execute_write(
            """
            INSERT INTO patients
                (first_name, last_name, date_of_birth, gender, phone, email, address, medical_history)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                request.form.get("first_name"),
                request.form.get("last_name"),
                request.form.get("date_of_birth") or None,
                request.form.get("gender"),
                request.form.get("phone"),
                request.form.get("email"),
                request.form.get("address"),
                request.form.get("medical_history"),
            ),
        )
        flash("Patient added successfully.", "success")
        return redirect(url_for("patients"))

    all_patients = fetch_all(
        """
        SELECT patient_id, first_name, last_name, date_of_birth, gender, phone, email,
               address, medical_history, created_at
        FROM patients
        ORDER BY patient_id DESC
        """
    )
    return render_template("patients.html", title="Patients", patients=all_patients)


@app.route("/doctors", methods=["GET", "POST"])
def doctors():
    if request.method == "POST":
        execute_write(
            """
            INSERT INTO doctors
                (full_name, specialization, phone, email, available_days, consultation_fee)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                request.form.get("full_name"),
                request.form.get("specialization"),
                request.form.get("phone"),
                request.form.get("email"),
                request.form.get("available_days"),
                request.form.get("consultation_fee") or 0,
            ),
        )
        flash("Doctor added successfully.", "success")
        return redirect(url_for("doctors"))

    all_doctors = fetch_all(
        """
        SELECT doctor_id, full_name, specialization, phone, email,
               available_days, consultation_fee, created_at
        FROM doctors
        ORDER BY doctor_id DESC
        """
    )
    return render_template("doctors.html", title="Doctors", doctors=all_doctors)


@app.route("/appointments", methods=["GET", "POST"])
def appointments():
    if request.method == "POST":
        execute_write(
            """
            INSERT INTO appointments
                (patient_id, doctor_id, appointment_date, appointment_time, consultation_type, reason, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'Pending')
            """,
            (
                request.form.get("patient_id"),
                request.form.get("doctor_id"),
                request.form.get("appointment_date"),
                request.form.get("appointment_time"),
                request.form.get("consultation_type"),
                request.form.get("reason"),
            ),
        )
        flash("Appointment booked successfully.", "success")
        return redirect(url_for("appointments"))

    patients_list = fetch_all(
        "SELECT patient_id, CONCAT(first_name, ' ', last_name) AS patient_name FROM patients ORDER BY first_name"
    )
    doctors_list = fetch_all(
        "SELECT doctor_id, full_name, specialization FROM doctors ORDER BY full_name"
    )
    appointment_list = fetch_all(
        """
        SELECT
            a.appointment_id,
            CONCAT(p.first_name, ' ', p.last_name) AS patient_name,
            d.full_name AS doctor_name,
            d.specialization,
            a.appointment_date,
            TIME_FORMAT(a.appointment_time, '%h:%i %p') AS appointment_time,
            a.consultation_type,
            a.reason,
            a.status,
            a.created_at
        FROM appointments a
        JOIN patients p ON a.patient_id = p.patient_id
        JOIN doctors d ON a.doctor_id = d.doctor_id
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
        """
    )
    return render_template(
        "appointments.html",
        title="Appointments",
        patients=patients_list,
        doctors=doctors_list,
        appointments=appointment_list,
    )


@app.route("/appointments/<int:appointment_id>/status", methods=["POST"])
def update_appointment_status(appointment_id):
    new_status = request.form.get("status")
    allowed_statuses = {"Pending", "Confirmed", "Completed", "Cancelled"}
    if new_status not in allowed_statuses:
        flash("Invalid appointment status.", "error")
        return redirect(url_for("appointments"))

    execute_write(
        "UPDATE appointments SET status = %s WHERE appointment_id = %s",
        (new_status, appointment_id),
    )
    flash("Appointment status updated.", "success")
    return redirect(url_for("appointments"))


@app.route("/medical-records", methods=["GET", "POST"])
def medical_records():
    if request.method == "POST":
        try:
            execute_write(
                """
                INSERT INTO medical_records
                    (appointment_id, diagnosis, treatment, prescription, doctor_notes, follow_up_date)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    request.form.get("appointment_id"),
                    request.form.get("diagnosis"),
                    request.form.get("treatment"),
                    request.form.get("prescription"),
                    request.form.get("doctor_notes"),
                    request.form.get("follow_up_date") or None,
                ),
            )
            flash("Medical record added successfully.", "success")
        except Error as error:
            flash(f"Could not add record: {error}", "error")
        return redirect(url_for("medical_records"))

    appointment_options = fetch_all(
        """
        SELECT
            a.appointment_id,
            CONCAT('Appointment #', a.appointment_id, ' - ', p.first_name, ' ', p.last_name,
                   ' with ', d.full_name, ' on ', DATE_FORMAT(a.appointment_date, '%Y-%m-%d')) AS label
        FROM appointments a
        JOIN patients p ON a.patient_id = p.patient_id
        JOIN doctors d ON a.doctor_id = d.doctor_id
        LEFT JOIN medical_records mr ON a.appointment_id = mr.appointment_id
        WHERE mr.record_id IS NULL
        ORDER BY a.appointment_date DESC
        """
    )
    records = fetch_all(
        """
        SELECT
            mr.record_id,
            mr.appointment_id,
            CONCAT(p.first_name, ' ', p.last_name) AS patient_name,
            d.full_name AS doctor_name,
            mr.diagnosis,
            mr.treatment,
            mr.prescription,
            mr.doctor_notes,
            mr.follow_up_date,
            mr.created_at
        FROM medical_records mr
        JOIN appointments a ON mr.appointment_id = a.appointment_id
        JOIN patients p ON a.patient_id = p.patient_id
        JOIN doctors d ON a.doctor_id = d.doctor_id
        ORDER BY mr.created_at DESC
        """
    )
    return render_template(
        "medical_records.html",
        title="Medical Records",
        appointment_options=appointment_options,
        records=records,
    )


if __name__ == "__main__":
    app.run(debug=True)

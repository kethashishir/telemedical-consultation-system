import os
from datetime import date, datetime

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
    "password": os.getenv("DB_PASSWORD", "TeleMedical2026!Project"),
    "database": os.getenv("DB_NAME", "telemedical_db"),
}

DAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

CONSULTATION_TYPES = {"Video Call", "Phone Call", "Chat"}
APPOINTMENT_STATUSES = {"Pending", "Confirmed", "Completed", "Cancelled"}


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


def parse_available_days(available_days):
    """Convert a stored string such as 'Monday, Wednesday' into a set of day names."""
    if not available_days:
        return set()

    separators_normalized = str(available_days)
    for separator in [";", "|", "/"]:
        separators_normalized = separators_normalized.replace(separator, ",")

    selected_days = set()
    for raw_value in separators_normalized.split(","):
        cleaned_value = raw_value.strip().lower()
        if not cleaned_value:
            continue

        for day_name in DAY_NAMES:
            if cleaned_value in {day_name.lower(), day_name[:3].lower()}:
                selected_days.add(day_name)
                break

    return selected_days


def format_available_days(days):
    """Return available days in Monday-Sunday order."""
    return ", ".join(day for day in DAY_NAMES if day in days)


def parse_iso_date(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


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
        selected_days = [day for day in DAY_NAMES if day in request.form.getlist("available_days")]
        if not selected_days:
            flash("Please select at least one available day for the doctor.", "error")
            return redirect(url_for("doctors"))

        try:
            consultation_fee = float(request.form.get("consultation_fee") or 0)
            if consultation_fee < 0:
                raise ValueError
        except ValueError:
            flash("Consultation fee must be a valid non-negative number.", "error")
            return redirect(url_for("doctors"))

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
                ", ".join(selected_days),
                consultation_fee,
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
    return render_template(
        "doctors.html",
        title="Doctors",
        doctors=all_doctors,
        day_names=DAY_NAMES,
    )


@app.route("/appointments", methods=["GET", "POST"])
def appointments():
    if request.method == "POST":
        patient_id = request.form.get("patient_id")
        doctor_id = request.form.get("doctor_id")
        appointment_date_value = request.form.get("appointment_date")
        appointment_time_value = request.form.get("appointment_time")
        consultation_type = request.form.get("consultation_type")
        reason = request.form.get("reason")

        errors = []
        appointment_date = None

        patient = fetch_one("SELECT patient_id FROM patients WHERE patient_id = %s", (patient_id,)) if patient_id else None
        doctor = fetch_one(
            "SELECT doctor_id, full_name, available_days FROM doctors WHERE doctor_id = %s",
            (doctor_id,),
        ) if doctor_id else None

        if not patient:
            errors.append("Please select a valid patient.")
        if not doctor:
            errors.append("Please select a valid doctor.")

        if not appointment_date_value:
            errors.append("Please select an appointment date.")
        else:
            try:
                appointment_date = parse_iso_date(appointment_date_value)
            except ValueError:
                errors.append("Please select a valid appointment date.")

        if appointment_date and appointment_date < date.today():
            errors.append("Appointment date cannot be in the past.")

        if not appointment_time_value:
            errors.append("Please select an appointment time.")
        else:
            try:
                datetime.strptime(appointment_time_value, "%H:%M")
            except ValueError:
                errors.append("Please select a valid appointment time.")

        if consultation_type not in CONSULTATION_TYPES:
            errors.append("Please select a valid consultation type.")

        if doctor and appointment_date:
            selected_day = appointment_date.strftime("%A")
            available_days = parse_available_days(doctor.get("available_days"))
            if not available_days:
                errors.append(f"{doctor['full_name']} does not have available days configured.")
            elif selected_day not in available_days:
                errors.append(
                    f"{doctor['full_name']} is available on {format_available_days(available_days)}. "
                    f"The selected date is a {selected_day}."
                )

        if doctor_id and appointment_date and appointment_time_value:
            existing_slot = fetch_one(
                """
                SELECT appointment_id
                FROM appointments
                WHERE doctor_id = %s
                  AND appointment_date = %s
                  AND appointment_time = %s
                  AND status <> 'Cancelled'
                LIMIT 1
                """,
                (doctor_id, appointment_date, appointment_time_value),
            )
            if existing_slot:
                errors.append("This doctor already has an appointment at the selected date and time.")

        if errors:
            for error in errors:
                flash(error, "error")
            return redirect(url_for("appointments"))

        execute_write(
            """
            INSERT INTO appointments
                (patient_id, doctor_id, appointment_date, appointment_time, consultation_type, reason, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'Pending')
            """,
            (
                patient_id,
                doctor_id,
                appointment_date,
                appointment_time_value,
                consultation_type,
                reason,
            ),
        )
        flash("Appointment booked successfully.", "success")
        return redirect(url_for("appointments"))

    patients_list = fetch_all(
        "SELECT patient_id, CONCAT(first_name, ' ', last_name) AS patient_name FROM patients ORDER BY first_name"
    )
    doctors_list = fetch_all(
        """
        SELECT doctor_id, full_name, specialization, available_days
        FROM doctors
        ORDER BY full_name
        """
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
        min_date=date.today().isoformat(),
    )


@app.route("/appointments/<int:appointment_id>/status", methods=["POST"])
def update_appointment_status(appointment_id):
    new_status = request.form.get("status")
    if new_status not in APPOINTMENT_STATUSES:
        flash("Invalid appointment status.", "error")
        return redirect(url_for("appointments"))

    appointment = fetch_one(
        "SELECT appointment_id FROM appointments WHERE appointment_id = %s",
        (appointment_id,),
    )
    if not appointment:
        flash("Appointment not found.", "error")
        return redirect(url_for("appointments"))

    existing_record = fetch_one(
        "SELECT record_id FROM medical_records WHERE appointment_id = %s",
        (appointment_id,),
    )
    if existing_record and new_status != "Completed":
        flash("This appointment has a medical record, so its status must remain Completed.", "error")
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
        appointment_id = request.form.get("appointment_id")
        diagnosis = request.form.get("diagnosis")
        follow_up_value = request.form.get("follow_up_date") or None
        follow_up_date = None
        errors = []

        appointment = fetch_one(
            """
            SELECT appointment_id, appointment_date, status
            FROM appointments
            WHERE appointment_id = %s
            """,
            (appointment_id,),
        ) if appointment_id else None

        if not appointment:
            errors.append("Please select a valid appointment.")
        elif appointment["status"] != "Completed":
            errors.append("Medical records can only be added for Completed appointments.")

        existing_record = fetch_one(
            "SELECT record_id FROM medical_records WHERE appointment_id = %s",
            (appointment_id,),
        ) if appointment_id else None
        if existing_record:
            errors.append("This appointment already has a medical record.")

        if not diagnosis:
            errors.append("Diagnosis is required.")

        if follow_up_value:
            try:
                follow_up_date = parse_iso_date(follow_up_value)
            except ValueError:
                errors.append("Please select a valid follow-up date.")

        if appointment and follow_up_date and follow_up_date < appointment["appointment_date"]:
            errors.append("Follow-up date cannot be before the appointment date.")

        if errors:
            for error in errors:
                flash(error, "error")
            return redirect(url_for("medical_records"))

        try:
            execute_write(
                """
                INSERT INTO medical_records
                    (appointment_id, diagnosis, treatment, prescription, doctor_notes, follow_up_date)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    appointment_id,
                    diagnosis,
                    request.form.get("treatment"),
                    request.form.get("prescription"),
                    request.form.get("doctor_notes"),
                    follow_up_date,
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
          AND a.status = 'Completed'
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

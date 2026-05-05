import os
from datetime import date, datetime, timedelta

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

GENDERS = {"Male", "Female", "Other"}
CONSULTATION_TYPES = {"Video Call", "Phone Call", "Chat"}
APPOINTMENT_STATUSES = {"Pending", "Confirmed", "Completed", "Cancelled"}
FUTURE_STATUS_VALUES = {"Pending", "Confirmed"}


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


def parse_time_value(value):
    if not value:
        return None
    parsed = datetime.strptime(value, "%H:%M").time()
    return parsed.strftime("%H:%M:%S")


def format_time_for_input(value):
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%H:%M")
    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        hours = (total_seconds // 3600) % 24
        minutes = (total_seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"

    value_text = str(value)
    try:
        parts = value_text.split(":")
        return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
    except (ValueError, IndexError):
        return value_text[:5]


def count_rows(sql, params=None):
    row = fetch_one(sql, params)
    return row["total"] if row else 0


def validate_patient_form():
    errors = []
    first_name = (request.form.get("first_name") or "").strip()
    last_name = (request.form.get("last_name") or "").strip()
    gender = request.form.get("gender")
    dob_value = request.form.get("date_of_birth") or None
    date_of_birth = None

    if not first_name:
        errors.append("First name is required.")
    if not last_name:
        errors.append("Last name is required.")
    if gender not in GENDERS:
        errors.append("Please select a valid gender.")

    if dob_value:
        try:
            date_of_birth = parse_iso_date(dob_value)
        except ValueError:
            errors.append("Please enter a valid date of birth.")
        else:
            if date_of_birth > date.today():
                errors.append("Date of birth cannot be in the future.")

    data = {
        "first_name": first_name,
        "last_name": last_name,
        "date_of_birth": date_of_birth,
        "gender": gender,
        "phone": (request.form.get("phone") or "").strip(),
        "email": (request.form.get("email") or "").strip(),
        "address": (request.form.get("address") or "").strip(),
        "medical_history": (request.form.get("medical_history") or "").strip(),
    }
    return data, errors


def validate_doctor_form(doctor_id=None):
    errors = []
    full_name = (request.form.get("full_name") or "").strip()
    specialization = (request.form.get("specialization") or "").strip()
    selected_days = [day for day in DAY_NAMES if day in request.form.getlist("available_days")]

    if not full_name:
        errors.append("Doctor full name is required.")
    if not specialization:
        errors.append("Specialization is required.")
    if not selected_days:
        errors.append("Please select at least one available day for the doctor.")

    try:
        consultation_fee = float(request.form.get("consultation_fee") or 0)
        if consultation_fee < 0:
            raise ValueError
    except ValueError:
        consultation_fee = 0
        errors.append("Consultation fee must be a valid non-negative number.")

    if doctor_id and selected_days:
        future_appointments = fetch_all(
            """
            SELECT appointment_id, appointment_date, status
            FROM appointments
            WHERE doctor_id = %s
              AND appointment_date >= %s
              AND status <> 'Cancelled'
            ORDER BY appointment_date
            """,
            (doctor_id, date.today()),
        )
        selected_day_set = set(selected_days)
        conflicts = []
        for appointment in future_appointments:
            appointment_day = appointment["appointment_date"].strftime("%A")
            if appointment_day not in selected_day_set:
                conflicts.append(
                    f"#{appointment['appointment_id']} on {appointment['appointment_date']} ({appointment_day})"
                )
        if conflicts:
            errors.append(
                "Cannot remove availability days because this doctor has future non-cancelled appointments: "
                + ", ".join(conflicts)
            )

    data = {
        "full_name": full_name,
        "specialization": specialization,
        "phone": (request.form.get("phone") or "").strip(),
        "email": (request.form.get("email") or "").strip(),
        "available_days": ", ".join(selected_days),
        "consultation_fee": consultation_fee,
        "selected_days": selected_days,
    }
    return data, errors


def validate_appointment_form(exclude_appointment_id=None):
    patient_id = request.form.get("patient_id")
    doctor_id = request.form.get("doctor_id")
    appointment_date_value = request.form.get("appointment_date")
    appointment_time_value = request.form.get("appointment_time")
    consultation_type = request.form.get("consultation_type")
    status = request.form.get("status") or "Pending"
    reason = (request.form.get("reason") or "").strip()

    errors = []
    appointment_date = None
    appointment_time = None

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

    if not appointment_time_value:
        errors.append("Please select an appointment time.")
    else:
        try:
            appointment_time = parse_time_value(appointment_time_value)
        except ValueError:
            errors.append("Please select a valid appointment time.")

    if consultation_type not in CONSULTATION_TYPES:
        errors.append("Please select a valid consultation type.")

    if status not in APPOINTMENT_STATUSES:
        errors.append("Please select a valid appointment status.")

    if appointment_date and status in FUTURE_STATUS_VALUES and appointment_date < date.today():
        errors.append("Pending or confirmed appointment dates cannot be in the past.")

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

    if doctor_id and appointment_date and appointment_time:
        params = [doctor_id, appointment_date, appointment_time]
        sql = """
            SELECT appointment_id
            FROM appointments
            WHERE doctor_id = %s
              AND appointment_date = %s
              AND appointment_time = %s
        """
        if exclude_appointment_id:
            sql += " AND appointment_id <> %s"
            params.append(exclude_appointment_id)
        sql += " LIMIT 1"
        existing_slot = fetch_one(sql, tuple(params))
        if existing_slot:
            errors.append("This doctor already has an appointment at the selected date and time.")

    data = {
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "appointment_date": appointment_date,
        "appointment_time": appointment_time,
        "consultation_type": consultation_type,
        "reason": reason,
        "status": status,
    }
    return data, errors


def validate_medical_record_form(appointment_id=None):
    diagnosis = (request.form.get("diagnosis") or "").strip()
    follow_up_value = request.form.get("follow_up_date") or None
    follow_up_date = None
    errors = []

    if not diagnosis:
        errors.append("Diagnosis is required.")

    if follow_up_value:
        try:
            follow_up_date = parse_iso_date(follow_up_value)
        except ValueError:
            errors.append("Please select a valid follow-up date.")

    appointment = None
    if appointment_id:
        appointment = fetch_one(
            """
            SELECT appointment_id, appointment_date, status
            FROM appointments
            WHERE appointment_id = %s
            """,
            (appointment_id,),
        )
        if not appointment:
            errors.append("Appointment not found.")
        elif appointment["status"] != "Completed":
            errors.append("Medical records can only be saved for Completed appointments.")

    if appointment and follow_up_date and follow_up_date < appointment["appointment_date"]:
        errors.append("Follow-up date cannot be before the appointment date.")

    data = {
        "diagnosis": diagnosis,
        "treatment": (request.form.get("treatment") or "").strip(),
        "prescription": (request.form.get("prescription") or "").strip(),
        "doctor_notes": (request.form.get("doctor_notes") or "").strip(),
        "follow_up_date": follow_up_date,
    }
    return data, errors


def flash_errors(errors):
    for error in errors:
        flash(error, "error")


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
        data, errors = validate_patient_form()
        if errors:
            flash_errors(errors)
            return redirect(url_for("patients"))

        execute_write(
            """
            INSERT INTO patients
                (first_name, last_name, date_of_birth, gender, phone, email, address, medical_history)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                data["first_name"],
                data["last_name"],
                data["date_of_birth"],
                data["gender"],
                data["phone"],
                data["email"],
                data["address"],
                data["medical_history"],
            ),
        )
        flash("Patient added successfully.", "success")
        return redirect(url_for("patients"))

    all_patients = fetch_all(
        """
        SELECT
            p.patient_id,
            p.first_name,
            p.last_name,
            p.date_of_birth,
            p.gender,
            p.phone,
            p.email,
            p.address,
            p.medical_history,
            p.created_at,
            COUNT(a.appointment_id) AS appointment_count
        FROM patients p
        LEFT JOIN appointments a ON p.patient_id = a.patient_id
        GROUP BY p.patient_id
        ORDER BY p.patient_id DESC
        """
    )
    return render_template("patients.html", title="Patients", patients=all_patients)


@app.route("/patients/<int:patient_id>/edit", methods=["GET", "POST"])
def edit_patient(patient_id):
    patient = fetch_one("SELECT * FROM patients WHERE patient_id = %s", (patient_id,))
    if not patient:
        flash("Patient not found.", "error")
        return redirect(url_for("patients"))

    if request.method == "POST":
        data, errors = validate_patient_form()
        if errors:
            flash_errors(errors)
            return redirect(url_for("edit_patient", patient_id=patient_id))

        execute_write(
            """
            UPDATE patients
            SET first_name = %s,
                last_name = %s,
                date_of_birth = %s,
                gender = %s,
                phone = %s,
                email = %s,
                address = %s,
                medical_history = %s
            WHERE patient_id = %s
            """,
            (
                data["first_name"],
                data["last_name"],
                data["date_of_birth"],
                data["gender"],
                data["phone"],
                data["email"],
                data["address"],
                data["medical_history"],
                patient_id,
            ),
        )
        flash("Patient updated successfully.", "success")
        return redirect(url_for("patients"))

    return render_template("patient_form.html", title="Edit Patient", patient=patient)


@app.route("/patients/<int:patient_id>/delete", methods=["POST"])
def delete_patient(patient_id):
    patient = fetch_one("SELECT patient_id FROM patients WHERE patient_id = %s", (patient_id,))
    if not patient:
        flash("Patient not found.", "error")
        return redirect(url_for("patients"))

    appointment_count = count_rows(
        "SELECT COUNT(*) AS total FROM appointments WHERE patient_id = %s",
        (patient_id,),
    )
    if appointment_count > 0:
        flash("Cannot delete this patient because they have appointments. Delete those appointments first.", "error")
        return redirect(url_for("patients"))

    execute_write("DELETE FROM patients WHERE patient_id = %s", (patient_id,))
    flash("Patient deleted successfully.", "success")
    return redirect(url_for("patients"))


@app.route("/doctors", methods=["GET", "POST"])
def doctors():
    if request.method == "POST":
        data, errors = validate_doctor_form()
        if errors:
            flash_errors(errors)
            return redirect(url_for("doctors"))

        execute_write(
            """
            INSERT INTO doctors
                (full_name, specialization, phone, email, available_days, consultation_fee)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                data["full_name"],
                data["specialization"],
                data["phone"],
                data["email"],
                data["available_days"],
                data["consultation_fee"],
            ),
        )
        flash("Doctor added successfully.", "success")
        return redirect(url_for("doctors"))

    all_doctors = fetch_all(
        """
        SELECT
            d.doctor_id,
            d.full_name,
            d.specialization,
            d.phone,
            d.email,
            d.available_days,
            d.consultation_fee,
            d.created_at,
            COUNT(a.appointment_id) AS appointment_count
        FROM doctors d
        LEFT JOIN appointments a ON d.doctor_id = a.doctor_id
        GROUP BY d.doctor_id
        ORDER BY d.doctor_id DESC
        """
    )
    return render_template(
        "doctors.html",
        title="Doctors",
        doctors=all_doctors,
        day_names=DAY_NAMES,
    )


@app.route("/doctors/<int:doctor_id>/edit", methods=["GET", "POST"])
def edit_doctor(doctor_id):
    doctor = fetch_one("SELECT * FROM doctors WHERE doctor_id = %s", (doctor_id,))
    if not doctor:
        flash("Doctor not found.", "error")
        return redirect(url_for("doctors"))

    if request.method == "POST":
        data, errors = validate_doctor_form(doctor_id=doctor_id)
        if errors:
            flash_errors(errors)
            return redirect(url_for("edit_doctor", doctor_id=doctor_id))

        execute_write(
            """
            UPDATE doctors
            SET full_name = %s,
                specialization = %s,
                phone = %s,
                email = %s,
                available_days = %s,
                consultation_fee = %s
            WHERE doctor_id = %s
            """,
            (
                data["full_name"],
                data["specialization"],
                data["phone"],
                data["email"],
                data["available_days"],
                data["consultation_fee"],
                doctor_id,
            ),
        )
        flash("Doctor updated successfully.", "success")
        return redirect(url_for("doctors"))

    selected_days = parse_available_days(doctor.get("available_days"))
    return render_template(
        "doctor_form.html",
        title="Edit Doctor",
        doctor=doctor,
        day_names=DAY_NAMES,
        selected_days=selected_days,
    )


@app.route("/doctors/<int:doctor_id>/delete", methods=["POST"])
def delete_doctor(doctor_id):
    doctor = fetch_one("SELECT doctor_id FROM doctors WHERE doctor_id = %s", (doctor_id,))
    if not doctor:
        flash("Doctor not found.", "error")
        return redirect(url_for("doctors"))

    appointment_count = count_rows(
        "SELECT COUNT(*) AS total FROM appointments WHERE doctor_id = %s",
        (doctor_id,),
    )
    if appointment_count > 0:
        flash("Cannot delete this doctor because they have appointments. Delete those appointments first.", "error")
        return redirect(url_for("doctors"))

    execute_write("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
    flash("Doctor deleted successfully.", "success")
    return redirect(url_for("doctors"))


@app.route("/appointments", methods=["GET", "POST"])
def appointments():
    if request.method == "POST":
        data, errors = validate_appointment_form()
        if errors:
            flash_errors(errors)
            return redirect(url_for("appointments"))

        execute_write(
            """
            INSERT INTO appointments
                (patient_id, doctor_id, appointment_date, appointment_time, consultation_type, reason, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'Pending')
            """,
            (
                data["patient_id"],
                data["doctor_id"],
                data["appointment_date"],
                data["appointment_time"],
                data["consultation_type"],
                data["reason"],
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
            a.created_at,
            mr.record_id
        FROM appointments a
        JOIN patients p ON a.patient_id = p.patient_id
        JOIN doctors d ON a.doctor_id = d.doctor_id
        LEFT JOIN medical_records mr ON a.appointment_id = mr.appointment_id
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


@app.route("/appointments/<int:appointment_id>/edit", methods=["GET", "POST"])
def edit_appointment(appointment_id):
    appointment = fetch_one("SELECT * FROM appointments WHERE appointment_id = %s", (appointment_id,))
    if not appointment:
        flash("Appointment not found.", "error")
        return redirect(url_for("appointments"))

    existing_record = fetch_one(
        "SELECT record_id FROM medical_records WHERE appointment_id = %s",
        (appointment_id,),
    )
    if existing_record:
        flash("This appointment already has a medical record, so appointment details are locked.", "error")
        return redirect(url_for("appointments"))

    if request.method == "POST":
        data, errors = validate_appointment_form(exclude_appointment_id=appointment_id)
        if errors:
            flash_errors(errors)
            return redirect(url_for("edit_appointment", appointment_id=appointment_id))

        execute_write(
            """
            UPDATE appointments
            SET patient_id = %s,
                doctor_id = %s,
                appointment_date = %s,
                appointment_time = %s,
                consultation_type = %s,
                reason = %s,
                status = %s
            WHERE appointment_id = %s
            """,
            (
                data["patient_id"],
                data["doctor_id"],
                data["appointment_date"],
                data["appointment_time"],
                data["consultation_type"],
                data["reason"],
                data["status"],
                appointment_id,
            ),
        )
        flash("Appointment updated successfully.", "success")
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
    appointment["appointment_time_value"] = format_time_for_input(appointment.get("appointment_time"))
    return render_template(
        "appointment_form.html",
        title="Edit Appointment",
        appointment=appointment,
        patients=patients_list,
        doctors=doctors_list,
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


@app.route("/appointments/<int:appointment_id>/delete", methods=["POST"])
def delete_appointment(appointment_id):
    appointment = fetch_one("SELECT appointment_id FROM appointments WHERE appointment_id = %s", (appointment_id,))
    if not appointment:
        flash("Appointment not found.", "error")
        return redirect(url_for("appointments"))

    existing_record = fetch_one(
        "SELECT record_id FROM medical_records WHERE appointment_id = %s",
        (appointment_id,),
    )
    if existing_record:
        flash("Cannot delete this appointment because it has a medical record. Delete the medical record first.", "error")
        return redirect(url_for("appointments"))

    execute_write("DELETE FROM appointments WHERE appointment_id = %s", (appointment_id,))
    flash("Appointment deleted successfully.", "success")
    return redirect(url_for("appointments"))


@app.route("/medical-records", methods=["GET", "POST"])
def medical_records():
    if request.method == "POST":
        appointment_id = request.form.get("appointment_id")
        appointment = fetch_one(
            """
            SELECT appointment_id, appointment_date, status
            FROM appointments
            WHERE appointment_id = %s
            """,
            (appointment_id,),
        ) if appointment_id else None

        errors = []
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

        data, record_errors = validate_medical_record_form(appointment_id=appointment_id)
        errors.extend(record_errors)

        if errors:
            flash_errors(errors)
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
                    data["diagnosis"],
                    data["treatment"],
                    data["prescription"],
                    data["doctor_notes"],
                    data["follow_up_date"],
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
            a.appointment_date,
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


@app.route("/medical-records/<int:record_id>/edit", methods=["GET", "POST"])
def edit_medical_record(record_id):
    record = fetch_one(
        """
        SELECT
            mr.*,
            a.appointment_date,
            a.status,
            CONCAT(p.first_name, ' ', p.last_name) AS patient_name,
            d.full_name AS doctor_name
        FROM medical_records mr
        JOIN appointments a ON mr.appointment_id = a.appointment_id
        JOIN patients p ON a.patient_id = p.patient_id
        JOIN doctors d ON a.doctor_id = d.doctor_id
        WHERE mr.record_id = %s
        """,
        (record_id,),
    )
    if not record:
        flash("Medical record not found.", "error")
        return redirect(url_for("medical_records"))

    if request.method == "POST":
        data, errors = validate_medical_record_form(appointment_id=record["appointment_id"])
        if errors:
            flash_errors(errors)
            return redirect(url_for("edit_medical_record", record_id=record_id))

        execute_write(
            """
            UPDATE medical_records
            SET diagnosis = %s,
                treatment = %s,
                prescription = %s,
                doctor_notes = %s,
                follow_up_date = %s
            WHERE record_id = %s
            """,
            (
                data["diagnosis"],
                data["treatment"],
                data["prescription"],
                data["doctor_notes"],
                data["follow_up_date"],
                record_id,
            ),
        )
        flash("Medical record updated successfully.", "success")
        return redirect(url_for("medical_records"))

    return render_template("medical_record_form.html", title="Edit Medical Record", record=record)


@app.route("/medical-records/<int:record_id>/delete", methods=["POST"])
def delete_medical_record(record_id):
    record = fetch_one("SELECT record_id FROM medical_records WHERE record_id = %s", (record_id,))
    if not record:
        flash("Medical record not found.", "error")
        return redirect(url_for("medical_records"))

    execute_write("DELETE FROM medical_records WHERE record_id = %s", (record_id,))
    flash("Medical record deleted successfully.", "success")
    return redirect(url_for("medical_records"))


if __name__ == "__main__":
    app.run(debug=True)

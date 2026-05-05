# Telemedical Consultation System - Project Report

## 1. Title Page

**Project Name:** Telemedical Consultation System  
**Course:** Database Systems  
**Instructor:** Dr. Howlader  

| Group Member Name | Student ID |
|---|---|
| Your Name | Your ID |
| Member 2 | ID |
| Member 3 | ID |
| Member 4 | ID |

## 2. Project Description

The Telemedical Consultation System is a database-driven web application designed to manage remote medical consultations. The system allows healthcare staff to register patients, add doctors, book consultation appointments, update appointment status, and record diagnosis, treatment, prescription, and follow-up information.

### Purpose and Background

Telemedicine is useful when patients need medical advice without physically visiting a clinic. A small clinic needs an organized system to store patient information, doctor information, appointment schedules, and consultation records. This project demonstrates how a MySQL relational database can support a real-world telemedical workflow.

### Key Features

- Add and view patients.
- Add and view doctors.
- Book telemedical appointments.
- Update appointment status.
- Add medical records after consultations.
- View dashboard summary counts.

### Design Considerations

The database is normalized into four main tables: Patients, Doctors, Appointments, and Medical Records. Foreign keys are used to maintain relationships and data integrity. The front-end is simple and easy to use so that a clinic staff member can quickly manage records.

## 3. Requirement / System Analysis

### Functional Requirements

1. The system shall allow users to add new patients.
2. The system shall allow users to add new doctors.
3. The system shall allow users to book appointments between patients and doctors.
4. The system shall allow users to update appointment status.
5. The system shall allow users to add medical records for appointments.
6. The system shall display dashboard statistics.

### Non-Functional Requirements

1. The system should be simple and easy to use.
2. The system should store data in MySQL.
3. The system should maintain relationships using primary keys and foreign keys.
4. The system should run locally on a MacBook for class demonstration.

## 4. ER Model

Insert the ER diagram image from `docs/er_diagram.png` here.

## 5. Relational Schema

### Patients

Patients(patient_id PK, first_name, last_name, date_of_birth, gender, phone, email, address, medical_history, created_at)

### Doctors

Doctors(doctor_id PK, full_name, specialization, phone, email, available_days, consultation_fee, created_at)

### Appointments

Appointments(appointment_id PK, patient_id FK, doctor_id FK, appointment_date, appointment_time, consultation_type, reason, status, created_at)

- patient_id references Patients(patient_id)
- doctor_id references Doctors(doctor_id)

### Medical Records

Medical_Records(record_id PK, appointment_id FK UNIQUE, diagnosis, treatment, prescription, doctor_notes, follow_up_date, created_at)

- appointment_id references Appointments(appointment_id)

## 6. Front-End Interface

### Dashboard

Purpose: Displays total patients, doctors, appointments, and medical records. It also shows recent appointments.

Insert screenshot here.

### Patients Page

Purpose: Allows the user to add patient information and view registered patients.

Insert screenshot here.

### Doctors Page

Purpose: Allows the user to add doctor information and view doctor details.

Insert screenshot here.

### Appointments Page

Purpose: Allows the user to book a telemedical appointment and update appointment status.

Insert screenshot here.

### Medical Records Page

Purpose: Allows the user to add diagnosis, treatment, prescription, and follow-up information.

Insert screenshot here.

## 7. Conclusion

The Telemedical Consultation System successfully demonstrates a complete database application with a front-end interface and a MySQL back-end. It uses ER modeling, relational schema design, primary keys, foreign keys, and a working web interface to manage telemedical consultations.

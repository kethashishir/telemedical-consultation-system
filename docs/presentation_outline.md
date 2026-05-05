# Telemedical Consultation System - Presentation Outline

## Slide 1: Title

Telemedical Consultation System  
Group Members: Add names and IDs

Speaker notes:
Good morning. Our final project is a Telemedical Consultation System. It is a database application that helps a clinic manage remote patient consultations.

## Slide 2: Project Purpose and Features

Purpose:
- Manage online medical consultation data.

Main features:
- Patient registration
- Doctor management
- Appointment booking
- Appointment status update
- Medical records and prescriptions

Speaker notes:
The purpose is to store and organize patient, doctor, appointment, and medical record information in one system.

## Slide 3: ER Model and Database Design

Tables:
- Patients
- Doctors
- Appointments
- Medical Records

Relationships:
- One patient can have many appointments.
- One doctor can have many appointments.
- One appointment can have one medical record.

Speaker notes:
Our database uses four related tables. Appointments connect patients and doctors, and medical records store consultation results.

## Slide 4: Front-End and Back-End

Front-end:
- Flask HTML pages
- Forms for adding data
- Tables for viewing records

Back-end:
- MySQL database
- Primary keys and foreign keys
- Python database connection

Speaker notes:
The front-end is built using Flask templates. The back-end uses MySQL. Python connects the forms to the database.

## Slide 5: Live Demo Plan

Demo steps:
1. Show dashboard.
2. Add a patient.
3. Add or show doctors.
4. Book an appointment.
5. Update appointment status.
6. Add a medical record.

Speaker notes:
Now we will demonstrate the working project by adding data and showing how it is saved in the database.

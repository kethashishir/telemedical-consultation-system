DROP TABLE IF EXISTS medical_records;
DROP TABLE IF EXISTS appointments;
DROP TABLE IF EXISTS doctors;
DROP TABLE IF EXISTS patients;

CREATE TABLE patients (
    patient_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    date_of_birth DATE,
    gender ENUM('Male', 'Female', 'Other') NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(100),
    address VARCHAR(255),
    medical_history TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE doctors (
    doctor_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    specialization VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(100),
    available_days VARCHAR(100),
    consultation_fee DECIMAL(10,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE appointments (
    appointment_id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    consultation_type ENUM('Video Call', 'Phone Call', 'Chat') NOT NULL,
    reason TEXT,
    status ENUM('Pending', 'Confirmed', 'Completed', 'Cancelled') DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_appointments_patient
        FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_appointments_doctor
        FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE medical_records (
    record_id INT AUTO_INCREMENT PRIMARY KEY,
    appointment_id INT NOT NULL UNIQUE,
    diagnosis VARCHAR(255) NOT NULL,
    treatment TEXT,
    prescription TEXT,
    doctor_notes TEXT,
    follow_up_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_records_appointment
        FOREIGN KEY (appointment_id) REFERENCES appointments(appointment_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

INSERT INTO patients (first_name, last_name, date_of_birth, gender, phone, email, address, medical_history) VALUES
('Aisha', 'Rahman', '1998-04-12', 'Female', '555-1001', 'aisha@example.com', 'Queens, NY', 'Seasonal allergies'),
('Michael', 'Smith', '1987-09-23', 'Male', '555-1002', 'michael@example.com', 'Brooklyn, NY', 'High blood pressure'),
('Sofia', 'Garcia', '2001-01-15', 'Female', '555-1003', 'sofia@example.com', 'Bronx, NY', 'No major history');

INSERT INTO doctors (full_name, specialization, phone, email, available_days, consultation_fee) VALUES
('Dr. Nadia Khan', 'General Medicine', '555-2001', 'nadia.khan@example.com', 'Monday, Wednesday, Friday', 50.00),
('Dr. James Lee', 'Cardiology', '555-2002', 'james.lee@example.com', 'Tuesday, Thursday', 85.00),
('Dr. Emily Carter', 'Dermatology', '555-2003', 'emily.carter@example.com', 'Monday, Thursday', 70.00);

INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, consultation_type, reason, status) VALUES
(1, 1, '2026-05-06', '10:00:00', 'Video Call', 'Fever and cough consultation', 'Confirmed'),
(2, 2, '2026-05-07', '14:30:00', 'Phone Call', 'Blood pressure follow-up', 'Pending'),
(3, 3, '2026-05-08', '11:15:00', 'Chat', 'Skin rash question', 'Pending');

INSERT INTO medical_records (appointment_id, diagnosis, treatment, prescription, doctor_notes, follow_up_date) VALUES
(1, 'Common cold symptoms', 'Rest, hydration, monitor temperature', 'Acetaminophen as needed', 'Patient advised to contact doctor if symptoms worsen.', '2026-05-13');

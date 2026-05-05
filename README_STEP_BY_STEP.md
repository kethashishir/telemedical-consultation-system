# Telemedical Consultation System - Step-by-Step Mac Setup

This project is a simple Flask + MySQL web application for a Database Systems final project.

## 1. Open Terminal and go to the project folder

If you put this folder on your Desktop:

```bash
cd ~/Desktop/"Telemedical Consultation System"
```

## 2. Install tools with Homebrew

If Homebrew is not installed, run:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Then install Python and MySQL:

```bash
brew update
brew install python mysql
brew services start mysql
```

## 3. Create MySQL database and user

Try this first:

```bash
mysql -u root <<'SQL'
CREATE DATABASE IF NOT EXISTS telemedical_db;
CREATE USER IF NOT EXISTS 'teleuser'@'localhost' IDENTIFIED BY 'telepass123';
GRANT ALL PRIVILEGES ON telemedical_db.* TO 'teleuser'@'localhost';
FLUSH PRIVILEGES;
SQL
```

If MySQL asks for a password, use this instead:

```bash
mysql -u root -p
```

Then paste these SQL commands manually:

```sql
CREATE DATABASE IF NOT EXISTS telemedical_db;
CREATE USER IF NOT EXISTS 'teleuser'@'localhost' IDENTIFIED BY 'telepass123';
GRANT ALL PRIVILEGES ON telemedical_db.* TO 'teleuser'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

## 4. Import the project tables and sample data

```bash
mysql -u teleuser -ptelepass123 telemedical_db < schema.sql
```

## 5. Create Python virtual environment and install packages

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 6. Create your local environment file

```bash
cp .env.example .env
```

## 7. Run the application

```bash
python app.py
```

Open your browser and go to:

```text
http://127.0.0.1:5000
```

## 8. Demo order for presentation

1. Dashboard: show total patients, doctors, appointments, and medical records.
2. Patients: add a new patient.
3. Doctors: add a doctor or show existing doctors.
4. Appointments: book a new appointment and update its status.
5. Medical Records: add diagnosis, treatment, and prescription for an appointment.
6. Explain that MySQL stores all data in four related tables.

## 9. Take screenshots for your report

On Mac, press `Shift + Command + 4`, select the screen area, and take screenshots of:

- Dashboard
- Patients page
- Doctors page
- Appointments page
- Medical Records page

Paste those screenshots into the report template.

## 10. Reset database if needed

This deletes old test data and reloads sample data:

```bash
mysql -u teleuser -ptelepass123 telemedical_db < schema.sql
```

## 11. Common fixes

If Flask cannot connect to MySQL:

```bash
brew services restart mysql
```

If the virtual environment is not active:

```bash
source venv/bin/activate
```

If you changed the MySQL password, update the `.env` file.


# 🏥 Clinic Management System

<div align="center">

![Django](https://img.shields.io/badge/Django-6.0-green?style=for-the-badge&logo=django)
![Angular](https://img.shields.io/badge/Angular-19-red?style=for-the-badge&logo=angular)
![MySQL](https://img.shields.io/badge/MySQL-8.0-blue?style=for-the-badge&logo=mysql)
![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-3.0-38B2AC?style=for-the-badge&logo=tailwind-css)
![DRF](https://img.shields.io/badge/DRF-3.17-ff1709?style=for-the-badge&logo=django)
![JWT](https://img.shields.io/badge/JWT-Auth-000000?style=for-the-badge&logo=jsonwebtokens)

**A full-stack clinic appointment management system with role-based access control, real-time queue management, and EMR-lite consultation records.**

[Features](#-features) · [Setup](#-setup--installation) · [API Docs](#-api-documentation) · [Sample Users](#-sample-users) · [Testing](#-testing)

</div>

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Tech Stack](#-tech-stack)
- [Database Schema](#-database-schema)
- [Setup & Installation](#-setup--installation)
- [Sample Users](#-sample-users)
- [API Documentation](#-api-documentation)
- [Running Tests](#-running-tests)
- [Project Structure](#-project-structure)

---

## 🔎 Overview

A comprehensive clinic management platform enabling:

| Role | Capabilities |
|------|-------------|
| **Patient** | Register, book appointments, view consultation summaries |
| **Doctor** | Manage schedule, daily queue, fill consultation records |
| **Receptionist** | Manage doctor availability, check-in patients, manage queue |
| **Admin** | Manage users/roles, analytics dashboard, CSV export |

---

## 🛠 Tech Stack

### Backend
| Technology | Purpose |
|-----------|---------|
| Django 6.0 | Web framework |
| Django REST Framework 3.17 | REST API |
| SimpleJWT | Authentication (Access + Refresh tokens) |
| MySQL 8.0 | Database |
| django-filter | Search & filtering |
| django-cors-headers | CORS handling |

### Frontend
| Technology | Purpose |
|-----------|---------|
| Angular 19 | SPA framework |
| Tailwind CSS 3 | Utility-first styling |


---

## 🗄 Database Schema

### ER Diagram

<img width="1770" height="923" alt="image" src="https://github.com/user-attachments/assets/314de516-5284-4d1a-be8a-46ca4ce232a9" />
https://dbdiagram.io/d/69d9511e0f7c9ef2c0cc7ff0


### Appointment Lifecycle (State Machine)

```
  ┌───────────┐    confirm    ┌───────────┐   check-in   ┌────────────┐   complete   ┌───────────┐
  │schedualed │──────────────▶│ CONFIRMED │─────────────▶│ CHECKED_IN │────────────▶│ COMPLETED │
  └───────────┘               └───────────┘              └────────────┘             └───────────┘
       │                           │                          │
       │  cancel                   │  cancel                  │  no-show
       ▼                           ▼                          ▼
  ┌───────────┐              ┌───────────┐              ┌──────────┐
  │ CANCELLED │              │ CANCELLED │              │ NO_SHOW  │
  └───────────┘              └───────────┘              └──────────┘
```



## 🚀 Setup & Installation

### Prerequisites

| Requirement | Version |
|------------|---------|
| Python | 3.12+ |
| Node.js | 18+ |
| MySQL | 8.0+ |
| Angular CLI | 19+ |

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/mahallawy1/django-project.git
cd clinic-management-system
```

### 2️⃣ Backend Setup

```bash
# Navigate to backend
cd clinic_management_system

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3️⃣ Database Configuration

Create a MySQL database:

```sql
CREATE DATABASE clinic_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'clinic_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON clinic_db.* TO 'clinic_user'@'localhost';
FLUSH PRIVILEGES;
```

Create a `.env` file in the backend root:

```env
DB_USER=
DB_PASSWORD=
DB_NAME=
DB_HOST=
DB_PORT=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

### 4️⃣ Run Migrations & Seed Data

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

```

### 5️⃣ Start Backend Server

```bash
python manage.py runserver
```

> Backend runs at: **http://127.0.0.1:8000**

### 6️⃣ Frontend Setup

```bash
# Navigate to frontend
cd clinic_management_front

# Install dependencies
npm install

# Start development server
ng serve
```

> Frontend runs at: **http://localhost:4200**

---

## 👥 Sample Users

Use these credentials to test each role:

| Role | username | Password | Notes |
|------|-------|----------|-------|
| **Admin** | `admin` | `admin` | Full system access |
| **Doctor** | `dr_handsome` | `asakaloldo` | women department |
| **Receptionist** | `hamada` | `iti123456` | Front desk management |
| **Patient** | `ammar` | `ammarkhaled` | Sample patient account |

---

## 📡 API Documentation

### 📎 Full API Reference

🔗 **[Notion API Documentation](https://www.notion.so/HMS-API-33d800b2c07880c59dbce76f08c614c7)**



## 🧪 Running Tests

```bash
# Navigate to backend directory
cd clinic_management_system

# Run all tests
python manage.py test

# Run with verbosity
python manage.py test -v 2

# Run specific app tests
python manage.py test appointments
python manage.py test doctors
python manage.py test users

# Run with coverage report
pip install coverage
coverage run manage.py test
coverage report -m
coverage html  # generates htmlcov/index.html
```

### Test Coverage Screenshot

<img width="687" height="648" alt="Untitled" src="https://github.com/user-attachments/assets/c29f6dd0-1275-464a-a5cd-23b6da6d410f" />

![Test Coverage](docs/screenshots/test_coverage.png)

---

## 📂 Project Structure

### Backend

```
clinic_management_system/
├── clinic_management_system/    # Project settings & root URLs
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── users/                       # Authentication, roles, admin management
│   ├── models.py               # Custom User model with roles
│   ├── permissions.py          # Role-based permission classes
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
├── doctors/                     # Doctor profiles, schedules, slot generation
│   ├── models.py               # DoctorProfile, WeeklySchedule, Exception, Slot
│   ├── services.py             # Slot generation logic
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
├── patients/                    # Patient profiles,Booking,
│   ├── models.py               # PatientProfile
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
├── appointments/                #  lifecycle, consultations
│   ├── models.py               # Appointment, Consultation, RescheduleHistory
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
├── receptionist/                # Receptionist-specific actions
│   ├── views.py
│   ├── urls.py
│   └── doctor_urls.py
├── requirements.txt
└── manage.py
```



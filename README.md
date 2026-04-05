# Clinic Management System

A lightweight Django clinic appointment system for managing doctor schedules, patient bookings, check-ins, and simple consultation records.

## Table of Contents
- [Objective](#objective)
- [Roles](#roles)
- [Required Features](#required-features)
- [Bonus Features](#bonus-features)
- [Technical Constraints](#technical-constraints)

## Objective

> Build a clinic system where patients book appointments, receptionists manage scheduling, and doctors manage consultations, with correct permissions, scheduling rules, and workflows.

## Roles

### Patient
- Register / login
- View / update own profile
- Book available appointment slots
- View own appointments (upcoming / history)
- Cancel (with policy) and request reschedule
- View consultation summary after completion (read-only)

### Doctor
- View own schedule and daily queue
- Confirm / decline appointment requests
- Mark checked-in / completed / no-show
- Fill consultation record (notes, diagnosis, prescriptions, tests)

### Receptionist
- Manage doctor schedules (weekly availability + exceptions)
- Confirm bookings (if clinic policy requires)
- Check-in patients and manage queue order
- Reschedule on behalf of patients
- Cannot access medical notes

### Admin
- Manage users and roles
- View analytics dashboard and export CSV reports

## Required Features

### 1) Doctor availability & slot generation
- Weekly schedule per doctor (day, start, end)
- Exceptions: vacations / day-offs and one-off working days
- Slot generation based on session duration (e.g., 15 or 30 minutes)
- Optional buffer time before/after slots (configurable, default: 5 minutes)

### 2) Booking & conflict rules
- Patients can book only available slots
- Prevent:
	- Double booking for the same doctor/time
	- Overlapping appointments for the same patient
- Enforce database-level constraints and transactional booking to avoid race conditions

### 3) Appointment lifecycle
- Statuses: `REQUESTED → CONFIRMED → CHECKED_IN → COMPLETED` (also `CANCELLED`, `NO_SHOW`)
- Rules:
	- Patients may cancel only when status is `REQUESTED` or `CONFIRMED`
	- Doctor or receptionist can mark `NO_SHOW`
	- `COMPLETED` requires the consultation record to be filled

### 4) Rescheduling & audit trail
- Allow reschedule requests by patients or staff
- Keep history for each change:
	- old datetime, new datetime, changed by, reason, timestamp

### 5) Queue / Check-in
- Receptionist checks in patients
- Doctor dashboard shows today's queue ordered by check-in time
- Show waiting time (e.g., `now - check_in_time`)

### 6) EMR Lite (Consultation record)
- For `COMPLETED` appointments store:
	- diagnosis, notes
	- prescription items (drug, dose, duration)
	- requested tests
- Patients can view consultation summaries (read-only)
- Receptionists cannot view medical notes

### 7) Search & filters
- Appointment list filters: status, date range, doctor, patient (staff only)
- Search by appointment id or patient name (staff only)
- Provide DRF API endpoints for appointments and slots

## Bonus Features (optional)
- Social login for patients (Facebook, Google / OAuth)
- Waiting list with auto-fill on cancellation (hold selection for 30 minutes)
- Payment simulation + refund policy + invoice PDF export
- Telemedicine support (online link + file sharing)
- Analytics dashboard (no-show rate, peak hours, revenue)
- Unit tests with coverage (aim: > 12 tests)

## Technical Constraints
- Use Django authentication, groups and permissions
- Prefer class-based views where reasonable
- Enforce booking uniqueness with database constraints
- Use transactions for booking and rescheduling operations

# QR-Based Attendance System

A secure Flask web application for managing student attendance using QR codes.

## Features

- **User Authentication**
  - Student login with registration number
  - Teacher login with email
  - Role-based access control

- **Teacher Features**
  - Create subjects for specific year and division
  - Generate time-limited QR codes for attendance
  - View attendance records by subject and date
  - Export attendance data

- **Student Features**
  - Enroll in subjects for their year/division
  - Scan QR codes to mark attendance
  - View personal attendance history
  - Real-time attendance status

- **Security Features**
  - Time-limited QR codes (5 minutes validity)
  - IP/Device tracking for attendance
  - Prevention of duplicate scans
  - Password hashing
  - Session management

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd attendance-system
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On Unix or MacOS
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory:
```
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///attendance.db
```

5. Initialize the database:
```bash
flask db init
flask db migrate
flask db upgrade
```

## Running the Application

1. Start the development server:
```bash
python run.py
```

2. Access the application at `http://localhost:5000`

## Project Structure

```
attendance-system/
├── app/
│   ├── __init__.py
│   ├── models/
│   │   └── models.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── main.py
│   │   ├── student.py
│   │   └── teacher.py
│   ├── static/
│   │   └── css/
│   └── templates/
│       ├── auth/
│       ├── student/
│       └── teacher/
├── requirements.txt
└── run.py
```

## Security Considerations

- QR codes are time-limited and expire after 5 minutes
- Each QR code can only be used once per student
- IP addresses and device information are logged
- Passwords are securely hashed using bcrypt
- Session data is encrypted
- CSRF protection is enabled

## Contributing

1. Fork the repository
2. Create a new branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

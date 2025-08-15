#!/usr/bin/env python3
"""
Database Viewer Script for Attendance System
"""

import os
import sys
from tabulate import tabulate

# Set environment variables directly
os.environ['SECRET_KEY'] = 'your-secret-key-here'
os.environ['DATABASE_URL'] = 'postgresql://sanket:LU9ZK9Fyiu0jwUxcfOBzZkNwNLImA9ag@dpg-d2fe9cer433s73b86oug-a.singapore-postgres.render.com/attendance_ostk'

def view_database():
    """View all data from the database"""
    try:
        from app import create_app, db
        from app.models.models import User, Subject, Attendance, QRCode, Enrollment
        
        app = create_app()
        
        with app.app_context():
            print("📊 Database Viewer for Attendance System")
            print("=" * 60)
            
            # View Users
            print("\n👥 USERS:")
            print("-" * 30)
            users = User.query.all()
            if users:
                user_data = []
                for user in users:
                    user_data.append([
                        user.id,
                        user.name,
                        user.email,
                        user.role,
                        user.registration_number,
                        user.created_at.strftime('%Y-%m-%d %H:%M') if user.created_at else 'N/A'
                    ])
                print(tabulate(user_data, headers=['ID', 'Name', 'Email', 'Role', 'Reg Number', 'Created'], tablefmt='grid'))
            else:
                print("No users found.")
            
            # View Subjects
            print("\n📚 SUBJECTS:")
            print("-" * 30)
            subjects = Subject.query.all()
            if subjects:
                subject_data = []
                for subject in subjects:
                    subject_data.append([
                        subject.id,
                        subject.name,
                        subject.year,
                        subject.division,
                        subject.teacher.name if subject.teacher else 'N/A',
                        subject.created_at.strftime('%Y-%m-%d %H:%M') if subject.created_at else 'N/A'
                    ])
                print(tabulate(subject_data, headers=['ID', 'Name', 'Year', 'Division', 'Teacher', 'Created'], tablefmt='grid'))
            else:
                print("No subjects found.")
            
            # View Enrollments
            print("\n📝 ENROLLMENTS:")
            print("-" * 30)
            enrollments = Enrollment.query.all()
            if enrollments:
                enrollment_data = []
                for enrollment in enrollments:
                    enrollment_data.append([
                        enrollment.id,
                        enrollment.student.name if enrollment.student else 'N/A',
                        enrollment.subject.name if enrollment.subject else 'N/A',
                        enrollment.roll_number,
                        enrollment.created_at.strftime('%Y-%m-%d %H:%M') if enrollment.created_at else 'N/A'
                    ])
                print(tabulate(enrollment_data, headers=['ID', 'Student', 'Subject', 'Roll Number', 'Created'], tablefmt='grid'))
            else:
                print("No enrollments found.")
            
            # View QR Codes
            print("\n📱 QR CODES:")
            print("-" * 30)
            qr_codes = QRCode.query.all()
            if qr_codes:
                qr_data = []
                for qr in qr_codes:
                    qr_data.append([
                        qr.id,
                        qr.subject.name if qr.subject else 'N/A',
                        qr.token[:20] + '...' if len(qr.token) > 20 else qr.token,
                        qr.is_active,
                        qr.created_at.strftime('%Y-%m-%d %H:%M') if qr.created_at else 'N/A'
                    ])
                print(tabulate(qr_data, headers=['ID', 'Subject', 'Token', 'Active', 'Created'], tablefmt='grid'))
            else:
                print("No QR codes found.")
            
            # View Attendance
            print("\n✅ ATTENDANCE RECORDS:")
            print("-" * 30)
            attendance_records = Attendance.query.all()
            if attendance_records:
                attendance_data = []
                for record in attendance_records:
                    attendance_data.append([
                        record.id,
                        record.student.name if record.student else 'N/A',
                        record.subject.name if record.subject else 'N/A',
                        record.qr_code.token[:10] + '...' if record.qr_code and len(record.qr_code.token) > 10 else 'N/A',
                        record.marked_at.strftime('%Y-%m-%d %H:%M') if record.marked_at else 'N/A'
                    ])
                print(tabulate(attendance_data, headers=['ID', 'Student', 'Subject', 'QR Token', 'Marked At'], tablefmt='grid'))
            else:
                print("No attendance records found.")
            
            # Summary
            print("\n📈 SUMMARY:")
            print("-" * 30)
            print(f"Total Users: {len(users)}")
            print(f"Total Subjects: {len(subjects)}")
            print(f"Total Enrollments: {len(enrollments)}")
            print(f"Total QR Codes: {len(qr_codes)}")
            print(f"Total Attendance Records: {len(attendance_records)}")
            
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Install tabulate: pip install tabulate")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    if view_database():
        print("\n✅ Database view completed successfully!")
    else:
        print("\n❌ Failed to view database!")
        sys.exit(1)

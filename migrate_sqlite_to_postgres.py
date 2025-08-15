#!/usr/bin/env python3
"""
Migrate data from SQLite to PostgreSQL
"""

import os
import sys
import sqlite3
from datetime import datetime

# Set environment variables for PostgreSQL
os.environ['SECRET_KEY'] = 'your-secret-key-here'
os.environ['DATABASE_URL'] = 'postgresql://sanket:LU9ZK9Fyiu0jwUxcfOBzZkNwNLImA9ag@dpg-d2fe9cer433s73b86oug-a.singapore-postgres.render.com/attendance_ostk'

def migrate_data():
    """Migrate data from SQLite to PostgreSQL"""
    try:
        from app import create_app, db
        from app.models.models import User, Subject, Attendance, QRCode, Enrollment
        from werkzeug.security import generate_password_hash
        
        print("🔄 Migrating data from SQLite to PostgreSQL...")
        print("=" * 60)
        
        # Connect to SQLite database
        sqlite_path = "instance/attendance.db"
        if not os.path.exists(sqlite_path):
            print("❌ SQLite database not found at instance/attendance.db")
            return False
        
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_cursor = sqlite_conn.cursor()
        
        # Create Flask app context for PostgreSQL
        app = create_app()
        
        with app.app_context():
            # Migrate Users
            print("\n👥 Migrating Users...")
            sqlite_cursor.execute("SELECT * FROM user")
            users = sqlite_cursor.fetchall()
            
            for user_data in users:
                # Check if user already exists
                existing_user = User.query.filter_by(email=user_data[1]).first()
                if not existing_user:
                    user = User(
                        email=user_data[1],
                        registration_number=user_data[2],
                        name=user_data[3],
                        password_hash=user_data[4],
                        role=user_data[5],
                        year=user_data[6],
                        division=user_data[7],
                        created_at=datetime.fromisoformat(user_data[8]) if user_data[8] else None
                    )
                    db.session.add(user)
                    print(f"  ✅ Added user: {user.name} ({user.email})")
                else:
                    print(f"  ⚠️  User already exists: {user_data[3]} ({user_data[1]})")
            
            db.session.commit()
            
            # Migrate Subjects
            print("\n📚 Migrating Subjects...")
            sqlite_cursor.execute("SELECT * FROM subject")
            subjects = sqlite_cursor.fetchall()
            
            for subject_data in subjects:
                # Check if subject already exists by name and teacher
                existing_subject = Subject.query.filter_by(
                    name=subject_data[1],
                    teacher_id=subject_data[3]
                ).first()
                
                if not existing_subject:
                    # Find teacher
                    teacher = User.query.filter_by(id=subject_data[3]).first() if subject_data[3] else None
                    
                    if teacher:
                        subject = Subject(
                            name=subject_data[1],
                            year=subject_data[2] if len(subject_data) > 2 else 1,  # Default to year 1
                            division=subject_data[4] if len(subject_data) > 4 else 'A',  # Default to division A
                            teacher_id=teacher.id,
                            created_at=datetime.fromisoformat(subject_data[5]) if len(subject_data) > 5 and subject_data[5] else None
                        )
                        db.session.add(subject)
                        print(f"  ✅ Added subject: {subject.name} (Teacher: {teacher.name})")
                    else:
                        print(f"  ⚠️  Teacher not found for subject: {subject_data[1]}")
                else:
                    print(f"  ⚠️  Subject already exists: {subject_data[1]}")
            
            db.session.commit()
            
            # Migrate Enrollments
            print("\n📝 Migrating Enrollments...")
            sqlite_cursor.execute("SELECT * FROM enrollment")
            enrollments = sqlite_cursor.fetchall()
            
            for enrollment_data in enrollments:
                # Check if enrollment already exists
                existing_enrollment = Enrollment.query.filter_by(
                    student_id=enrollment_data[1],
                    subject_id=enrollment_data[2]
                ).first()
                
                if not existing_enrollment:
                    enrollment = Enrollment(
                        student_id=enrollment_data[1],
                        subject_id=enrollment_data[2],
                        roll_number=enrollment_data[3] if len(enrollment_data) > 3 else 1,
                        created_at=datetime.fromisoformat(enrollment_data[4]) if len(enrollment_data) > 4 and enrollment_data[4] else None
                    )
                    db.session.add(enrollment)
                    print(f"  ✅ Added enrollment: Student {enrollment_data[1]} -> Subject {enrollment_data[2]}")
                else:
                    print(f"  ⚠️  Enrollment already exists: Student {enrollment_data[1]} -> Subject {enrollment_data[2]}")
            
            db.session.commit()
            
            # Migrate QR Codes
            print("\n📱 Migrating QR Codes...")
            sqlite_cursor.execute("SELECT * FROM qr_code")
            qr_codes = sqlite_cursor.fetchall()
            
            for qr_data in qr_codes:
                # Check if QR code already exists
                existing_qr = QRCode.query.filter_by(token=qr_data[2]).first()
                if not existing_qr:
                    qr_code = QRCode(
                        subject_id=qr_data[1],
                        token=qr_data[2],
                        created_at=datetime.fromisoformat(qr_data[3]) if len(qr_data) > 3 and qr_data[3] else None,
                        expires_at=datetime.fromisoformat(qr_data[4]) if len(qr_data) > 4 and qr_data[4] else datetime.utcnow(),
                        is_active=bool(qr_data[5]) if len(qr_data) > 5 else True,
                        class_start_time=datetime.fromisoformat(qr_data[6]) if len(qr_data) > 6 and qr_data[6] else None,
                        class_end_time=datetime.fromisoformat(qr_data[7]) if len(qr_data) > 7 and qr_data[7] else None
                    )
                    db.session.add(qr_code)
                    print(f"  ✅ Added QR code: {qr_code.token}")
                else:
                    print(f"  ⚠️  QR code already exists: {qr_data[2]}")
            
            db.session.commit()
            
            # Migrate Attendance
            print("\n✅ Migrating Attendance Records...")
            sqlite_cursor.execute("SELECT * FROM attendance")
            attendance_records = sqlite_cursor.fetchall()
            
            for attendance_data in attendance_records:
                # Check if attendance record already exists
                existing_attendance = Attendance.query.filter_by(
                    student_id=attendance_data[1],
                    subject_id=attendance_data[2],
                    qr_code_id=attendance_data[3]
                ).first()
                
                if not existing_attendance:
                    attendance = Attendance(
                        student_id=attendance_data[1],
                        subject_id=attendance_data[2],
                        qr_code_id=attendance_data[3],
                        marked_at=datetime.fromisoformat(attendance_data[4]) if len(attendance_data) > 4 and attendance_data[4] else None,
                        ip_address=attendance_data[5] if len(attendance_data) > 5 else None,
                        device_info=attendance_data[6] if len(attendance_data) > 6 else None
                    )
                    db.session.add(attendance)
                    print(f"  ✅ Added attendance record: Student {attendance_data[1]} -> Subject {attendance_data[2]}")
                else:
                    print(f"  ⚠️  Attendance record already exists: Student {attendance_data[1]} -> Subject {attendance_data[2]}")
            
            db.session.commit()
            
            sqlite_conn.close()
            
            print("\n🎉 Migration completed successfully!")
            print("✅ All data has been migrated from SQLite to PostgreSQL")
            
            # Show summary
            print("\n📊 Migration Summary:")
            print(f"  Users migrated: {len(users)}")
            print(f"  Subjects migrated: {len(subjects)}")
            print(f"  Enrollments migrated: {len(enrollments)}")
            print(f"  QR Codes migrated: {len(qr_codes)}")
            print(f"  Attendance records migrated: {len(attendance_records)}")
            
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    if migrate_data():
        print("\n✅ Migration completed successfully!")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)

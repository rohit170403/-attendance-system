from .. import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)
    registration_number = db.Column(db.String(20), unique=True)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'teacher' or 'student'
    year = db.Column(db.Integer)  # For students
    division = db.Column(db.String(10))  # For students
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    division = db.Column(db.String(10), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    teacher = db.relationship('User', backref='subjects')

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    roll_number = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    student = db.relationship('User', backref='enrollments')
    subject = db.relationship('Subject', backref='enrollments')
    
    __table_args__ = (
        db.UniqueConstraint('student_id', 'subject_id', name='unique_enrollment'),
    )

class QRCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    token = db.Column(db.String(200), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    class_start_time = db.Column(db.DateTime, nullable=True)
    class_end_time = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    subject = db.relationship('Subject', backref='qr_codes')

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    qr_code_id = db.Column(db.Integer, db.ForeignKey('qr_code.id'), nullable=False)
    marked_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))
    device_info = db.Column(db.String(200))
    
    # Relationships
    student = db.relationship('User', backref='attendances')
    subject = db.relationship('Subject', backref='attendances')
    qr_code = db.relationship('QRCode', backref='attendances')
    
    __table_args__ = (
        db.UniqueConstraint('student_id', 'qr_code_id', name='unique_attendance'),
    )

class LeaveApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    leave_type = db.Column(db.String(50), nullable=False)  # 'sick', 'personal', 'emergency', etc.
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected'
    teacher_remarks = db.Column(db.Text)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    
    # Relationships
    student = db.relationship('User', backref='leave_applications')
    subject = db.relationship('Subject', backref='leave_applications')

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    exam_type = db.Column(db.String(50), nullable=False)
    marks_obtained = db.Column(db.Float, nullable=False)
    max_marks = db.Column(db.Float, nullable=False)
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    student = db.relationship('User', backref='results')
    subject = db.relationship('Subject', backref='results')

    __table_args__ = (
        db.UniqueConstraint('student_id', 'subject_id', 'exam_type', name='unique_result_per_exam'),
    )
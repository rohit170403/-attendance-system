from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_required, current_user
from ..models.models import Subject, QRCode, Attendance, User, Enrollment, db
from datetime import datetime, timedelta
from functools import wraps
import qrcode
import io
import base64
import secrets
import json
import csv

teacher_bp = Blueprint('teacher', __name__)

def teacher_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != 'teacher':
            flash('Access denied.', 'error')
            return redirect(url_for('teacher.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@teacher_bp.route('/teacher/dashboard')
@teacher_required
def dashboard():
    subjects = Subject.query.filter_by(teacher_id=current_user.id).all()
    # Load enrollments for each subject to avoid lazy loading issues
    for subject in subjects:
        _ = subject.enrollments  # This triggers the relationship loading
    return render_template('teacher/dashboard.html', subjects=subjects)

@teacher_bp.route('/teacher/subject/create', methods=['GET', 'POST'])
@teacher_required
def create_subject():
    if request.method == 'POST':
        name = request.form.get('name')
        year = request.form.get('year')
        division = request.form.get('division')
        
        subject = Subject(
            name=name,
            year=year,
            division=division,
            teacher_id=current_user.id
        )
        db.session.add(subject)
        db.session.commit()
        
        flash('Subject created successfully!', 'success')
        return redirect(url_for('teacher.dashboard'))
        
    return render_template('teacher/create_subject.html')

@teacher_bp.route('/teacher/subject/<int:subject_id>/generate-qr', methods=['GET', 'POST'])
@teacher_required
def generate_qr(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    
    if subject.teacher_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('teacher.dashboard'))
    
    if request.method == 'POST':
        # Get class timing from form
        class_start_time = request.form.get('class_start_time')
        class_end_time = request.form.get('class_end_time')
        
        if not class_start_time or not class_end_time:
            flash('Please provide both start and end times.', 'error')
            return render_template('teacher/generate_qr_form.html', subject=subject)
        
        # Parse datetime strings
        try:
            start_time = datetime.strptime(class_start_time, '%Y-%m-%dT%H:%M')
            end_time = datetime.strptime(class_end_time, '%Y-%m-%dT%H:%M')
            
            if start_time >= end_time:
                flash('End time must be after start time.', 'error')
                return render_template('teacher/generate_qr_form.html', subject=subject)
                
        except ValueError:
            flash('Invalid date/time format.', 'error')
            return render_template('teacher/generate_qr_form.html', subject=subject)
        
        # Create QR code token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(seconds=30)  # QR valid for 30 seconds
        
        qr_code = QRCode(
            subject_id=subject_id,
            token=token,
            expires_at=expires_at,
            class_start_time=start_time,
            class_end_time=end_time
        )
        db.session.add(qr_code)
        db.session.commit()
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr_data = {
            'token': token,
            'subject_id': subject_id,
            'expires_at': expires_at.isoformat(),
            'class_start_time': start_time.isoformat(),
            'class_end_time': end_time.isoformat()
        }
        qr.add_data(json.dumps(qr_data))
        qr.make(fit=True)
        
        # Create QR image
        img = qr.make_image(fill_color="black", back_color="white")
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_str = base64.b64encode(img_buffer.getvalue()).decode()
        
        return render_template('teacher/show_qr.html', 
                             qr_image=img_str, 
                             subject=subject,
                             expires_at=expires_at,
                             class_start_time=start_time,
                             class_end_time=end_time)
    
    return render_template('teacher/generate_qr_form.html', subject=subject)

@teacher_bp.route('/teacher/subject/<int:subject_id>/attendance')
@teacher_required
def view_attendance(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    
    if subject.teacher_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('teacher.dashboard'))
    
    # Load enrollments to avoid lazy loading issues
    _ = subject.enrollments
    
    date = request.args.get('date', datetime.utcnow().date().isoformat())
    
    # Get all attendance records for the subject on the specified date with class timing
    attendance_records = db.session.query(
        User.name, 
        User.registration_number,
        Enrollment.roll_number,
        Attendance.marked_at,
        Attendance.ip_address,
        QRCode.class_start_time,
        QRCode.class_end_time
    ).join(
        Attendance, User.id == Attendance.student_id
    ).join(
        Enrollment, User.id == Enrollment.student_id
    ).join(
        QRCode, Attendance.qr_code_id == QRCode.id
    ).filter(
        Attendance.subject_id == subject_id,
        db.func.date(Attendance.marked_at) == date
    ).all()
    
    return render_template('teacher/attendance.html',
                         subject=subject,
                         attendance_records=attendance_records,
                         date=date)

@teacher_bp.route('/teacher/subject/<int:subject_id>/export')
@teacher_required
def export_attendance(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    
    if subject.teacher_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('teacher.dashboard'))
    
    # Load enrollments to avoid lazy loading issues
    _ = subject.enrollments
    
    date = request.args.get('date', datetime.utcnow().date().isoformat())
    
    # Get all attendance records for the subject on the specified date with class timing
    attendance_records = db.session.query(
        User.name, 
        User.registration_number,
        Enrollment.roll_number,
        Attendance.marked_at,
        Attendance.ip_address,
        QRCode.class_start_time,
        QRCode.class_end_time
    ).join(
        Attendance, User.id == Attendance.student_id
    ).join(
        Enrollment, User.id == Enrollment.student_id
    ).join(
        QRCode, Attendance.qr_code_id == QRCode.id
    ).filter(
        Attendance.subject_id == subject_id,
        db.func.date(Attendance.marked_at) == date
    ).all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Roll Number', 'Name', 'Registration Number', 'Class Time', 'Marked At', 'IP Address'])
    
    for record in attendance_records:
        # Handle null class timing (for old QR codes)
        start_time = record.class_start_time.strftime('%H:%M') if record.class_start_time else 'N/A'
        end_time = record.class_end_time.strftime('%H:%M') if record.class_end_time else 'N/A'
        
        writer.writerow([
            record.roll_number,
            record.name,
            record.registration_number,
            f"{start_time} - {end_time}",
            record.marked_at.strftime('%H:%M:%S'),
            record.ip_address
        ])
    
    output.seek(0)
    
    filename = f"attendance_{subject.name}_{date}.csv"
    
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

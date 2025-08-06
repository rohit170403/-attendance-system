from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from ..models.models import Subject, QRCode, Attendance, Enrollment, db
from datetime import datetime
from functools import wraps
import json

student_bp = Blueprint('student', __name__)

def student_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != 'student':
            flash('Access denied.', 'error')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@student_bp.route('/student/dashboard')
@student_required
def dashboard():
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    return render_template('student/dashboard.html', enrollments=enrollments)

@student_bp.route('/student/subjects')
@student_required
def available_subjects():
    # Get subjects matching student's year and division
    subjects = Subject.query.filter_by(
        year=current_user.year,
        division=current_user.division
    ).all()
    
    # Get student's current enrollments
    enrolled_subject_ids = {
        enrollment.subject_id 
        for enrollment in Enrollment.query.filter_by(student_id=current_user.id).all()
    }
    
    return render_template('student/subjects.html', 
                         subjects=subjects,
                         enrolled_subject_ids=enrolled_subject_ids)

@student_bp.route('/student/enroll/<int:subject_id>', methods=['POST'])
@student_required
def enroll_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    
    # Verify student's year and division match the subject
    if subject.year != current_user.year or subject.division != current_user.division:
        flash('You cannot enroll in this subject.', 'error')
        return redirect(url_for('student.available_subjects'))
    
    # Check if already enrolled
    if Enrollment.query.filter_by(
        student_id=current_user.id,
        subject_id=subject_id
    ).first():
        flash('Already enrolled in this subject.', 'error')
        return redirect(url_for('student.available_subjects'))
    
    # Get the next available roll number for this subject
    last_enrollment = Enrollment.query.filter_by(
        subject_id=subject_id
    ).order_by(Enrollment.roll_number.desc()).first()
    
    next_roll = 1 if not last_enrollment else last_enrollment.roll_number + 1
    
    enrollment = Enrollment(
        student_id=current_user.id,
        subject_id=subject_id,
        roll_number=next_roll
    )
    db.session.add(enrollment)
    db.session.commit()
    
    flash('Successfully enrolled in the subject!', 'success')
    return redirect(url_for('student.dashboard'))

@student_bp.route('/student/mark-attendance', methods=['POST'])
@student_required
def mark_attendance():
    qr_data = request.json.get('qr_data')
    
    try:
        data = json.loads(qr_data)
        token = data.get('token')
        subject_id = data.get('subject_id')
        
        # Verify QR code
        qr_code = QRCode.query.filter_by(
            token=token,
            subject_id=subject_id,
            is_active=True
        ).first()
        
        if not qr_code:
            return jsonify({'error': 'Invalid QR code'}), 400
            
        # Check if QR is expired
        if datetime.utcnow() > qr_code.expires_at:
            return jsonify({'error': 'QR code has expired'}), 400
            
        # Check if student is enrolled in the subject
        enrollment = Enrollment.query.filter_by(
            student_id=current_user.id,
            subject_id=subject_id
        ).first()
        
        if not enrollment:
            return jsonify({'error': 'You are not enrolled in this subject'}), 400
            
        # Check if attendance already marked
        if Attendance.query.filter_by(
            student_id=current_user.id,
            qr_code_id=qr_code.id
        ).first():
            return jsonify({'error': 'Attendance already marked'}), 400
            
        # Mark attendance
        attendance = Attendance(
            student_id=current_user.id,
            subject_id=subject_id,
            qr_code_id=qr_code.id,
            ip_address=request.remote_addr,
            device_info=request.headers.get('User-Agent', '')
        )
        db.session.add(attendance)
        db.session.commit()
        
        # Return success with class timing information
        return jsonify({
            'message': 'Attendance marked successfully',
            'class_start_time': qr_code.class_start_time.strftime('%Y-%m-%d %H:%M') if qr_code.class_start_time else 'N/A',
            'class_end_time': qr_code.class_end_time.strftime('%Y-%m-%d %H:%M') if qr_code.class_end_time else 'N/A'
        })
        
    except Exception as e:
        return jsonify({'error': 'Invalid QR code format'}), 400

@student_bp.route('/student/attendance')
@student_required
def view_attendance():
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    attendance_data = []
    
    for enrollment in enrollments:
        # Get all QR codes for this subject with class timing
        qr_codes = QRCode.query.filter_by(
            subject_id=enrollment.subject_id
        ).all()
        
        # Get attendance records for this student and subject
        attendance_records = Attendance.query.filter_by(
            student_id=current_user.id,
            subject_id=enrollment.subject_id
        ).all()
        
        # Create a list of class sessions with attendance status
        class_sessions = []
        for qr_code in qr_codes:
            attended = any(record.qr_code_id == qr_code.id for record in attendance_records)
            # Handle null class timing (for old QR codes)
            start_time = qr_code.class_start_time.strftime('%H:%M') if qr_code.class_start_time else 'N/A'
            end_time = qr_code.class_end_time.strftime('%H:%M') if qr_code.class_end_time else 'N/A'
            
            class_sessions.append({
                'date': qr_code.created_at.strftime('%Y-%m-%d'),
                'start_time': start_time,
                'end_time': end_time,
                'attended': attended,
                'status': 'Present' if attended else 'Absent'
            })
        
        total_sessions = len(qr_codes)
        attended_sessions = len([s for s in class_sessions if s['attended']])
        percentage = (attended_sessions / total_sessions * 100) if total_sessions > 0 else 0
        
        attendance_data.append({
            'subject': Subject.query.get(enrollment.subject_id),
            'total_sessions': total_sessions,
            'attended_sessions': attended_sessions,
            'percentage': round(percentage, 2),
            'class_sessions': class_sessions
        })
    
    return render_template('student/attendance.html', attendance_data=attendance_data)

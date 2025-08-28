from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_required, current_user
from ..models.models import Subject, QRCode, Attendance, Enrollment, LeaveApplication, Result, db
from datetime import datetime, date
from functools import wraps
import json
from ..utils.results import calculate_percentage, calculate_grade, generate_report_pdf

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

@student_bp.route('/student/chatbot', methods=['POST'])
@student_required
def chatbot():
    """Chatbot API endpoint to handle student queries"""
    data = request.get_json()
    message = data.get('message', '').lower().strip()
    
    # Get student's enrollment and attendance data
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    
    # Calculate attendance statistics
    total_sessions = 0
    attended_sessions = 0
    attendance_by_subject = {}
    
    for enrollment in enrollments:
        subject = Subject.query.get(enrollment.subject_id)
        qr_codes = QRCode.query.filter_by(subject_id=enrollment.subject_id).all()
        attendance_records = Attendance.query.filter_by(
            student_id=current_user.id,
            subject_id=enrollment.subject_id
        ).all()
        
        subject_sessions = len(qr_codes)
        subject_attended = len(attendance_records)
        
        total_sessions += subject_sessions
        attended_sessions += subject_attended
        
        if subject_sessions > 0:
            percentage = (subject_attended / subject_sessions) * 100
            attendance_by_subject[subject.name] = {
                'total': subject_sessions,
                'attended': subject_attended,
                'percentage': round(percentage, 2)
            }
    
    overall_percentage = (attended_sessions / total_sessions * 100) if total_sessions > 0 else 0
    
    # Process different types of queries
    if any(word in message for word in ['attendance', 'present', 'absent', 'percentage']):
        if total_sessions == 0:
            response = "You haven't attended any classes yet. Start by enrolling in subjects and attending classes!"
        else:
            response = f"📊 **Your Attendance Summary:**\n\n"
            response += f"• **Overall Attendance:** {attended_sessions}/{total_sessions} ({round(overall_percentage, 2)}%)\n\n"
            
            if attendance_by_subject:
                response += "**By Subject:**\n"
                for subject_name, stats in attendance_by_subject.items():
                    status_emoji = "✅" if stats['percentage'] >= 75 else "⚠️" if stats['percentage'] >= 50 else "❌"
                    response += f"• {subject_name}: {stats['attended']}/{stats['total']} ({stats['percentage']}%) {status_emoji}\n"
                
                if overall_percentage >= 75:
                    response += "\n🎉 Great job! Your attendance is excellent!"
                elif overall_percentage >= 50:
                    response += "\n⚠️ Your attendance needs improvement. Try to attend more classes!"
                else:
                    response += "\n❌ Your attendance is low. Please make sure to attend all classes!"
    
    elif any(word in message for word in ['fees', 'payment', 'paid', 'due']):
        response = "💰 **Fee Information:**\n\n"
        response += "• **Tuition Fee:** ₹50,000 per semester\n"
        response += "• **Due Date:** 15th of each month\n"
        response += "• **Payment Status:** Please contact the administration office for current fee status\n"
        response += "• **Payment Methods:** Online banking, UPI, or cash at the office\n\n"
        response += "💡 **Need Help?** Contact the accounts department at accounts@college.edu"
    
    elif any(word in message for word in ['subject', 'course', 'enrolled']):
        if enrollments:
            response = "📚 **Your Enrolled Subjects:**\n\n"
            for enrollment in enrollments:
                subject = Subject.query.get(enrollment.subject_id)
                response += f"• **{subject.name}** (Year {subject.year}, Division {subject.division})\n"
                response += f"  Roll Number: {enrollment.roll_number}\n"
                response += f"  Teacher: {subject.teacher.name}\n\n"
        else:
            response = "📚 You haven't enrolled in any subjects yet.\n\n"
            response += "Go to 'Browse Subjects' to enroll in available courses!"
    
    elif any(word in message for word in ['schedule', 'timetable', 'class', 'time']):
        response = "📅 **Class Schedule:**\n\n"
        response += "**Monday - Friday:**\n"
        response += "• 9:00 AM - 10:00 AM: Morning Assembly\n"
        response += "• 10:00 AM - 11:00 AM: Period 1\n"
        response += "• 11:00 AM - 12:00 PM: Period 2\n"
        response += "• 12:00 PM - 1:00 PM: Lunch Break\n"
        response += "• 1:00 PM - 2:00 PM: Period 3\n"
        response += "• 2:00 PM - 3:00 PM: Period 4\n"
        response += "• 3:00 PM - 4:00 PM: Period 5\n\n"
        response += "**Saturday:**\n"
        response += "• 9:00 AM - 12:00 PM: Practical/Lab Sessions\n\n"
        response += "💡 Check your specific subject timings in the 'My Subjects' section!"
    
    elif any(word in message for word in ['help', 'support', 'assistance']):
        response = "🤖 **How can I help you?**\n\n"
        response += "I can provide information about:\n"
        response += "• 📊 **Attendance** - Check your attendance records\n"
        response += "• 💰 **Fees** - Fee structure and payment details\n"
        response += "• 📚 **Subjects** - Your enrolled courses\n"
        response += "• 📅 **Schedule** - Class timings and schedule\n"
        response += "• 👤 **Profile** - Your personal information\n\n"
        response += "Just ask me about any of these topics!"
    
    elif any(word in message for word in ['profile', 'personal', 'info', 'details']):
        response = f"👤 **Your Profile Information:**\n\n"
        response += f"• **Name:** {current_user.name}\n"
        response += f"• **Email:** {current_user.email}\n"
        response += f"• **Registration Number:** {current_user.registration_number}\n"
        response += f"• **Year:** {current_user.year}\n"
        response += f"• **Division:** {current_user.division}\n"
        response += f"• **Member Since:** {current_user.created_at.strftime('%B %Y')}\n\n"
        response += "💡 To update your information, contact the administration office."
    
    elif any(word in message for word in ['hello', 'hi', 'hey', 'greetings']):
        response = f"👋 **Hello {current_user.name}!**\n\n"
        response += "Welcome to your student dashboard! I'm your AI assistant.\n\n"
        response += "I can help you with:\n"
        response += "• Attendance information\n"
        response += "• Fee details\n"
        response += "• Subject information\n"
        response += "• Class schedule\n"
        response += "• Profile details\n\n"
        response += "Just ask me anything!"
    
    else:
        response = "🤔 I'm not sure I understand. Try asking about:\n\n"
        response += "• Your attendance records\n"
        response += "• Fee information\n"
        response += "• Enrolled subjects\n"
        response += "• Class schedule\n"
        response += "• Your profile\n\n"
        response += "Or type 'help' for more options!"
    
    return jsonify({
        'response': response,
        'timestamp': datetime.now().strftime('%H:%M')
    })

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

@student_bp.route('/student/leave-application', methods=['GET', 'POST'])
@student_required
def leave_application():
    if request.method == 'POST':
        subject_id = request.form.get('subject_id')
        leave_type = request.form.get('leave_type')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        reason = request.form.get('reason')
        
        # Validate inputs
        if not all([subject_id, leave_type, start_date, end_date, reason]):
            flash('Please fill in all fields.', 'error')
            return redirect(url_for('student.leave_application'))
        
        # Check if student is enrolled in the subject
        enrollment = Enrollment.query.filter_by(
            student_id=current_user.id,
            subject_id=subject_id
        ).first()
        
        if not enrollment:
            flash('You are not enrolled in this subject.', 'error')
            return redirect(url_for('student.leave_application'))
        
        # Validate dates
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            if start_date > end_date:
                flash('Start date cannot be after end date.', 'error')
                return redirect(url_for('student.leave_application'))
                
            if start_date < date.today():
                flash('Start date cannot be in the past.', 'error')
                return redirect(url_for('student.leave_application'))
                
        except ValueError:
            flash('Invalid date format.', 'error')
            return redirect(url_for('student.leave_application'))
        
        # Create leave application
        leave_app = LeaveApplication(
            student_id=current_user.id,
            subject_id=subject_id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            reason=reason
        )
        
        db.session.add(leave_app)
        db.session.commit()
        
        flash('Leave application submitted successfully!', 'success')
        return redirect(url_for('student.view_leave_applications'))
    
    # GET request - show form
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    subjects = [enrollment.subject for enrollment in enrollments]
    
    return render_template('student/leave_application.html', subjects=subjects)

@student_bp.route('/student/view-leave-applications')
@student_required
def view_leave_applications():
    leave_applications = LeaveApplication.query.filter_by(
        student_id=current_user.id
    ).order_by(LeaveApplication.submitted_at.desc()).all()
    
    return render_template('student/view_leave_applications.html', 
                         leave_applications=leave_applications)


@student_bp.route('/student/results')
@student_required
def view_results():
    results = db.session.query(Result, Subject).join(Subject, Result.subject_id == Subject.id).\
        filter(Result.student_id == current_user.id).\
        order_by(Subject.name.asc(), Result.exam_type.asc()).all()

    rows = []
    total_marks = 0.0
    total_max = 0.0
    for res, subj in results:
        pct = calculate_percentage(res.marks_obtained, res.max_marks)
        rows.append({
            'subject_name': subj.name,
            'exam_type': res.exam_type,
            'marks_obtained': res.marks_obtained,
            'max_marks': res.max_marks,
            'percentage': pct,
            'remarks': res.remarks
        })
        total_marks += (res.marks_obtained or 0)
        total_max += (res.max_marks or 0)

    overall_percentage = calculate_percentage(total_marks, total_max)
    overall_grade = calculate_grade(overall_percentage)

    # Attendance percentage: sessions attended / sessions total across enrolled subjects
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    subject_ids = [e.subject_id for e in enrollments]
    total_sessions = 0
    attended_sessions = 0
    if subject_ids:
        from ..models.models import QRCode  # local import to avoid cycle
        total_sessions = QRCode.query.filter(QRCode.subject_id.in_(subject_ids)).count()
        attended_sessions = Attendance.query.filter(Attendance.student_id == current_user.id, Attendance.subject_id.in_(subject_ids)).count()
    attendance_pct = (attended_sessions / total_sessions * 100.0) if total_sessions > 0 else 0.0

    return render_template('student/results.html', rows=rows, total_marks=total_marks, total_max=total_max,
                           overall_percentage=overall_percentage, overall_grade=overall_grade,
                           attendance_pct=round(attendance_pct, 2))


@student_bp.route('/student/results/report.pdf')
@student_required
def download_report_pdf():
    results = db.session.query(Result, Subject).join(Subject, Result.subject_id == Subject.id).\
        filter(Result.student_id == current_user.id).\
        order_by(Subject.name.asc(), Result.exam_type.asc()).all()

    rows = []
    total_marks = 0.0
    total_max = 0.0
    for res, subj in results:
        pct = calculate_percentage(res.marks_obtained, res.max_marks)
        rows.append({
            'subject_name': subj.name,
            'exam_type': res.exam_type,
            'marks_obtained': res.marks_obtained,
            'max_marks': res.max_marks,
            'percentage': pct,
            'remarks': res.remarks
        })
        total_marks += (res.marks_obtained or 0)
        total_max += (res.max_marks or 0)

    overall_percentage = calculate_percentage(total_marks, total_max)
    overall_grade = calculate_grade(overall_percentage)

    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    subject_ids = [e.subject_id for e in enrollments]
    total_sessions = 0
    attended_sessions = 0
    if subject_ids:
        from ..models.models import QRCode  # local import to avoid cycle
        total_sessions = QRCode.query.filter(QRCode.subject_id.in_(subject_ids)).count()
        attended_sessions = Attendance.query.filter(Attendance.student_id == current_user.id, Attendance.subject_id.in_(subject_ids)).count()
    attendance_pct = (attended_sessions / total_sessions * 100.0) if total_sessions > 0 else 0.0

    pdf_buffer = generate_report_pdf(current_user, rows, total_marks, total_max, overall_percentage, overall_grade, attendance_pct)
    return send_file(pdf_buffer, mimetype='application/pdf', as_attachment=True, download_name='report_card.pdf')

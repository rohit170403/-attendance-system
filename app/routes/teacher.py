from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file, session
from flask_login import login_required, current_user
from ..models.models import Subject, QRCode, Attendance, User, Enrollment, LeaveApplication, Result, db
from datetime import datetime, timedelta
from functools import wraps
import qrcode
import io
import base64
import secrets
import json
import csv
from collections import defaultdict
from ..utils.results import calculate_percentage

teacher_bp = Blueprint('teacher', __name__)

def teacher_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != 'teacher':
            flash('Access denied.', 'error')
            return redirect(url_for('student.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@teacher_bp.route('/teacher/dashboard')
@teacher_required
def dashboard():
    subjects = Subject.query.filter_by(teacher_id=current_user.id).all()
    # Load enrollments for each subject to avoid lazy loading issues
    for subject in subjects:
        _ = subject.enrollments  # This triggers the relationship loading
    current_expiry_seconds = session.get('qr_expiry_seconds', 30)
    return render_template('teacher/dashboard.html', subjects=subjects, qr_expiry_seconds=current_expiry_seconds)

@teacher_bp.route('/teacher/qr-expiry', methods=['POST'])
@teacher_required
def set_qr_expiry():
    try:
        value = request.form.get('expiry_value')
        unit = request.form.get('expiry_unit', 'seconds')
        if not value:
            flash('Please provide an expiry value.', 'error')
            return redirect(url_for('teacher.dashboard'))
        try:
            numeric = int(value)
        except ValueError:
            flash('Expiry value must be an integer.', 'error')
            return redirect(url_for('teacher.dashboard'))

        if numeric <= 0:
            flash('Expiry value must be greater than zero.', 'error')
            return redirect(url_for('teacher.dashboard'))

        seconds = numeric * 60 if unit == 'minutes' else numeric
        # Cap to a reasonable max (e.g., 2 hours)
        seconds = min(seconds, 2 * 60 * 60)
        session['qr_expiry_seconds'] = seconds
        flash(f'QR expiry set to {seconds} seconds.', 'success')
    except Exception:
        flash('Failed to update QR expiry.', 'error')
    return redirect(url_for('teacher.dashboard'))

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
        # Get expiry from form (value + unit)
        expiry_value = request.form.get('expiry_value')
        expiry_unit = request.form.get('expiry_unit', 'seconds')
        
        if not class_start_time or not class_end_time:
            flash('Please provide both start and end times.', 'error')
            return render_template('teacher/generate_qr_form.html', subject=subject, qr_expiry_seconds=session.get('qr_expiry_seconds', 30))
        
        # Parse datetime strings
        try:
            start_time = datetime.strptime(class_start_time, '%Y-%m-%dT%H:%M')
            end_time = datetime.strptime(class_end_time, '%Y-%m-%dT%H:%M')
            
            if start_time >= end_time:
                flash('End time must be after start time.', 'error')
                return render_template('teacher/generate_qr_form.html', subject=subject)
                
        except ValueError:
            flash('Invalid date/time format.', 'error')
            return render_template('teacher/generate_qr_form.html', subject=subject, qr_expiry_seconds=session.get('qr_expiry_seconds', 30))
        
        # Create QR code token
        token = secrets.token_urlsafe(32)
        # Determine expiry seconds: form value overrides session/default
        try:
            if expiry_value:
                numeric = int(expiry_value)
                if numeric <= 0:
                    raise ValueError('Expiry must be > 0')
                expiry_seconds = numeric * 60 if expiry_unit == 'minutes' else numeric
            else:
                expiry_seconds = session.get('qr_expiry_seconds', 30)
        except Exception:
            flash('Invalid expiry value provided.', 'error')
            return render_template('teacher/generate_qr_form.html', subject=subject, qr_expiry_seconds=session.get('qr_expiry_seconds', 30))
        # Cap expiry to max 2 hours
        expiry_seconds = min(expiry_seconds, 2 * 60 * 60)
        expires_at = datetime.utcnow() + timedelta(seconds=expiry_seconds)
        
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
    
    return render_template('teacher/generate_qr_form.html', subject=subject, qr_expiry_seconds=session.get('qr_expiry_seconds', 30))

@teacher_bp.route('/teacher/results', methods=['GET'])
@teacher_required
def results_hub():
    subjects = Subject.query.filter_by(teacher_id=current_user.id).all()
    students = User.query.filter_by(role='student').all()
    return render_template('teacher/results_manage.html', subjects=subjects, students=students)

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

@teacher_bp.route('/teacher/leave-applications')
@teacher_required
def leave_applications():
    """View all leave applications for teacher's subjects"""
    # Get all subjects taught by this teacher
    teacher_subjects = Subject.query.filter_by(teacher_id=current_user.id).all()
    subject_ids = [subject.id for subject in teacher_subjects]
    
    # Get all leave applications for these subjects
    leave_applications = LeaveApplication.query.filter(
        LeaveApplication.subject_id.in_(subject_ids)
    ).order_by(LeaveApplication.submitted_at.desc()).all()
    
    return render_template('teacher/leave_applications.html', 
                         leave_applications=leave_applications,
                         subjects=teacher_subjects)

@teacher_bp.route('/teacher/leave-applications/<int:subject_id>')
@teacher_required
def subject_leave_applications(subject_id):
    """View leave applications for a specific subject"""
    subject = Subject.query.get_or_404(subject_id)
    
    # Check if teacher owns this subject
    if subject.teacher_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('teacher.leave_applications'))
    
    leave_applications = LeaveApplication.query.filter_by(
        subject_id=subject_id
    ).order_by(LeaveApplication.submitted_at.desc()).all()
    
    return render_template('teacher/subject_leave_applications.html', 
                         leave_applications=leave_applications,
                         subject=subject)

@teacher_bp.route('/teacher/leave-application/<int:app_id>/review', methods=['POST'])
@teacher_required
def review_leave_application(app_id):
    """Review (approve/reject) a leave application"""
    try:
        print(f"DEBUG: Route called with app_id={app_id}")
        print(f"DEBUG: Form data: {request.form}")
        
        leave_app = LeaveApplication.query.get_or_404(app_id)
        print(f"DEBUG: Found leave application: {leave_app.id}")
        
        # Check if teacher owns the subject
        if leave_app.subject.teacher_id != current_user.id:
            print(f"DEBUG: Access denied - teacher_id mismatch")
            flash('Access denied.', 'error')
            return redirect(url_for('teacher.leave_applications'))
        
        action = request.form.get('action')
        remarks = request.form.get('remarks', '').strip()
        
        print(f"DEBUG: Received action={action}, remarks={remarks}")
        
        if not action:
            print(f"DEBUG: No action provided")
            flash('No action specified.', 'error')
            return redirect(url_for('teacher.leave_applications'))
        
        if action not in ['approve', 'reject']:
            print(f"DEBUG: Invalid action: {action}")
            flash('Invalid action.', 'error')
            return redirect(url_for('teacher.leave_applications'))
        
        # Update application status
        leave_app.status = 'approved' if action == 'approve' else 'rejected'
        leave_app.teacher_remarks = remarks
        leave_app.reviewed_at = datetime.utcnow()
        
        db.session.commit()
        print(f"DEBUG: Database updated successfully")
        
        status_text = 'approved' if action == 'approve' else 'rejected'
        flash(f'Leave application {status_text} successfully!', 'success')
        
        return redirect(url_for('teacher.leave_applications'))
    except Exception as e:
        print(f"DEBUG: Error in review_leave_application: {str(e)}")
        import traceback
        traceback.print_exc()
        flash('An error occurred while processing the request.', 'error')
        return redirect(url_for('teacher.leave_applications'))

@teacher_bp.route('/teacher/analytics')
@teacher_required
def analytics():
    subject_ids = [s.id for s in Subject.query.filter_by(teacher_id=current_user.id).all()]
    if not subject_ids:
        return render_template('teacher/analytics.html',
                               daily_labels=[], daily_values=[],
                               weekly_labels=[], weekly_values=[],
                               monthly_labels=[], monthly_values=[],
                               heatmap=[], subjects_meta=[],
                               defaulters=[],
                               generated_at=datetime.utcnow())

    # Enrollment counts per subject
    enrollment_counts_rows = db.session.query(Enrollment.subject_id, db.func.count(Enrollment.id)).\
        filter(Enrollment.subject_id.in_(subject_ids)).group_by(Enrollment.subject_id).all()
    enrollment_counts = {sid: cnt for sid, cnt in enrollment_counts_rows}

    # Daily trends (last 30 days)
    today = datetime.utcnow().date()
    last_30 = [today - timedelta(days=i) for i in range(29, -1, -1)]
    qr_rows = db.session.query(QRCode.subject_id, db.func.date(QRCode.class_start_time)).\
        filter(QRCode.subject_id.in_(subject_ids)).\
        filter(QRCode.class_start_time.isnot(None)).all()
    sessions_by_day = defaultdict(set)
    for sid, day in qr_rows:
        if day is not None:
            sessions_by_day[day].add(sid)
    att_rows = db.session.query(db.func.date(Attendance.marked_at), db.func.count(Attendance.id)).\
        filter(Attendance.subject_id.in_(subject_ids)).\
        group_by(db.func.date(Attendance.marked_at)).all()
    attendance_by_day = {day: cnt for day, cnt in att_rows}
    daily_labels = [d.strftime('%Y-%m-%d') for d in last_30]
    daily_values = []
    for d in last_30:
        sid_set = sessions_by_day.get(d, set())
        denom = sum(enrollment_counts.get(s, 0) for s in sid_set)
        numer = attendance_by_day.get(d, 0)
        pct = round((numer / denom) * 100, 2) if denom > 0 else 0
        daily_values.append(pct)

    # Weekly trends (last 8 weeks)
    def week_start(date_obj):
        return date_obj - timedelta(days=date_obj.weekday())
    daily_pct_map = {last_30[i]: daily_values[i] for i in range(len(last_30))}
    for i in range(1, 8 * 7 + 1):
        d = today - timedelta(days=i)
        if d not in daily_pct_map:
            daily_pct_map[d] = 0
    by_week = defaultdict(list)
    for d, pct in daily_pct_map.items():
        by_week[week_start(d)].append(pct)
    week_keys_sorted = sorted(list(by_week.keys()))[-8:]
    weekly_labels = [wk.strftime('%Y-%m-%d') for wk in week_keys_sorted]
    weekly_values = [round(sum(vals) / len(vals), 2) if vals else 0 for wk, vals in [(wk, by_week[wk]) for wk in week_keys_sorted]]

    # Monthly trends (last 12 months)
    qr_month_rows = db.session.query(QRCode.subject_id, db.func.date_trunc('month', QRCode.class_start_time)).\
        filter(QRCode.subject_id.in_(subject_ids)).\
        filter(QRCode.class_start_time.isnot(None)).all()
    sessions_by_month = defaultdict(set)
    for sid, month_dt in qr_month_rows:
        if month_dt is not None:
            sessions_by_month[month_dt.date()].add(sid)
    att_month_rows = db.session.query(db.func.date_trunc('month', Attendance.marked_at), db.func.count(Attendance.id)).\
        filter(Attendance.subject_id.in_(subject_ids)).\
        group_by(db.func.date_trunc('month', Attendance.marked_at)).all()
    attendance_by_month = {month_dt.date(): cnt for month_dt, cnt in att_month_rows}
    monthly_labels = []
    monthly_values = []
    first_of_month = datetime.utcnow().date().replace(day=1)
    months = []
    for i in range(11, -1, -1):
        y = first_of_month.year
        m = first_of_month.month - i
        while m <= 0:
            y -= 1
            m += 12
        months.append(datetime(y, m, 1).date())
    for mkey in months:
        sid_set = sessions_by_month.get(mkey, set())
        denom = sum(enrollment_counts.get(s, 0) for s in sid_set)
        numer = attendance_by_month.get(mkey, 0)
        pct = round((numer / denom) * 100, 2) if denom > 0 else 0
        monthly_labels.append(mkey.strftime('%Y-%m'))
        monthly_values.append(pct)

    # Heatmap over last 30 days per subject
    start_day = last_30[0]
    end_day = last_30[-1]
    subject_sessions_rows = db.session.query(QRCode.subject_id, db.func.count(QRCode.id)).\
        filter(QRCode.subject_id.in_(subject_ids)).\
        filter(QRCode.class_start_time.isnot(None)).\
        filter(db.func.date(QRCode.class_start_time) >= start_day).\
        filter(db.func.date(QRCode.class_start_time) <= end_day).\
        group_by(QRCode.subject_id).all()
    sessions_per_subject = {sid: cnt for sid, cnt in subject_sessions_rows}
    att_per_subject_rows = db.session.query(Attendance.subject_id, db.func.count(Attendance.id)).\
        filter(Attendance.subject_id.in_(subject_ids)).\
        filter(db.func.date(Attendance.marked_at) >= start_day).\
        filter(db.func.date(Attendance.marked_at) <= end_day).\
        group_by(Attendance.subject_id).all()
    att_per_subject = {sid: cnt for sid, cnt in att_per_subject_rows}
    heatmap = []
    subjects_meta = []
    for sid in subject_ids:
        subj = Subject.query.get(sid)
        subjects_meta.append({'id': sid, 'name': subj.name, 'division': subj.division})
        total_sessions = sessions_per_subject.get(sid, 0)
        denom = total_sessions * enrollment_counts.get(sid, 0)
        numer = att_per_subject.get(sid, 0)
        pct = round((numer / denom) * 100, 2) if denom > 0 else 0
        heatmap.append({'subject_id': sid, 'pct': pct})

    # Defaulters (< 75%)
    enrollments = Enrollment.query.filter(Enrollment.subject_id.in_(subject_ids)).all()
    student_subjects = defaultdict(set)
    for enr in enrollments:
        student_subjects[enr.student_id].add(enr.subject_id)
    att_student_rows = db.session.query(Attendance.student_id, db.func.count(db.func.distinct(Attendance.qr_code_id))).\
        filter(Attendance.subject_id.in_(subject_ids)).\
        group_by(Attendance.student_id).all()
    attended_by_student = {sid: cnt for sid, cnt in att_student_rows}
    defaulters = []
    for student_id, subs in student_subjects.items():
        total_sess = sum(sessions_per_subject.get(s, 0) for s in subs)
        attended = attended_by_student.get(student_id, 0)
        pct = round((attended / total_sess) * 100, 2) if total_sess > 0 else 0
        if pct < 75:
            user = User.query.get(student_id)
            defaulters.append({
                'student_id': student_id,
                'name': user.name if user else 'Unknown',
                'registration_number': user.registration_number if user else '',
                'attended': attended,
                'total': total_sess,
                'percentage': pct,
            })

    return render_template('teacher/analytics.html',
                           daily_labels=daily_labels, daily_values=daily_values,
                           weekly_labels=weekly_labels, weekly_values=weekly_values,
                           monthly_labels=monthly_labels, monthly_values=monthly_values,
                           heatmap=heatmap, subjects_meta=subjects_meta,
                           defaulters=defaulters,
                           generated_at=datetime.utcnow())

@teacher_bp.route('/teacher/analytics/defaulters.csv')
@teacher_required
def export_defaulters_csv():
    subject_ids = [s.id for s in Subject.query.filter_by(teacher_id=current_user.id).all()]
    subject_sessions_rows = db.session.query(QRCode.subject_id, db.func.count(QRCode.id)).\
        filter(QRCode.subject_id.in_(subject_ids)).\
        filter(QRCode.class_start_time.isnot(None)).\
        group_by(QRCode.subject_id).all()
    sessions_per_subject = {sid: cnt for sid, cnt in subject_sessions_rows}
    enrollments = Enrollment.query.filter(Enrollment.subject_id.in_(subject_ids)).all()
    student_subjects = defaultdict(set)
    for enr in enrollments:
        student_subjects[enr.student_id].add(enr.subject_id)
    att_student_rows = db.session.query(Attendance.student_id, db.func.count(db.func.distinct(Attendance.qr_code_id))).\
        filter(Attendance.subject_id.in_(subject_ids)).\
        group_by(Attendance.student_id).all()
    attended_by_student = {sid: cnt for sid, cnt in att_student_rows}
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Registration Number', 'Name', 'Attended', 'Total Sessions', 'Percentage'])
    for student_id, subs in student_subjects.items():
        total_sess = sum(sessions_per_subject.get(s, 0) for s in subs)
        attended = attended_by_student.get(student_id, 0)
        pct = round((attended / total_sess) * 100, 2) if total_sess > 0 else 0
        if pct < 75:
            user = User.query.get(student_id)
            writer.writerow([
                user.registration_number if user else '',
                user.name if user else 'Unknown',
                attended,
                total_sess,
                pct
            ])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode('utf-8')),
                     mimetype='text/csv',
                     as_attachment=True,
                     download_name='defaulters.csv')

@teacher_bp.route('/teacher/analytics/defaulters.pdf')
@teacher_required
def export_defaulters_pdf():
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    subject_ids = [s.id for s in Subject.query.filter_by(teacher_id=current_user.id).all()]
    subject_sessions_rows = db.session.query(QRCode.subject_id, db.func.count(QRCode.id)).\
        filter(QRCode.subject_id.in_(subject_ids)).\
        filter(QRCode.class_start_time.isnot(None)).\
        group_by(QRCode.subject_id).all()
    sessions_per_subject = {sid: cnt for sid, cnt in subject_sessions_rows}
    enrollments = Enrollment.query.filter(Enrollment.subject_id.in_(subject_ids)).all()
    student_subjects = defaultdict(set)
    for enr in enrollments:
        student_subjects[enr.student_id].add(enr.subject_id)
    att_student_rows = db.session.query(Attendance.student_id, db.func.count(db.func.distinct(Attendance.qr_code_id))).\
        filter(Attendance.subject_id.in_(subject_ids)).\
        group_by(Attendance.student_id).all()
    attended_by_student = {sid: cnt for sid, cnt in att_student_rows}
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - inch
    c.setFont("Helvetica-Bold", 14)
    c.drawString(inch, y, "Defaulters Report (Below 75%)")
    y -= 0.3 * inch
    c.setFont("Helvetica", 10)
    c.drawString(inch, y, f"Generated at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    y -= 0.4 * inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(inch, y, "Reg. No")
    c.drawString(inch + 1.5 * inch, y, "Name")
    c.drawString(inch + 4.0 * inch, y, "Attended")
    c.drawString(inch + 5.0 * inch, y, "Total")
    c.drawString(inch + 5.8 * inch, y, "%")
    y -= 0.2 * inch
    c.setFont("Helvetica", 10)
    for student_id, subs in student_subjects.items():
        total_sess = sum(sessions_per_subject.get(s, 0) for s in subs)
        attended = attended_by_student.get(student_id, 0)
        pct = round((attended / total_sess) * 100, 2) if total_sess > 0 else 0
        if pct < 75:
            user = User.query.get(student_id)
            if y < inch:
                c.showPage()
                y = height - inch
                c.setFont("Helvetica-Bold", 10)
                c.drawString(inch, y, "Reg. No")
                c.drawString(inch + 1.5 * inch, y, "Name")
                c.drawString(inch + 4.0 * inch, y, "Attended")
                c.drawString(inch + 5.0 * inch, y, "Total")
                c.drawString(inch + 5.8 * inch, y, "%")
                y -= 0.2 * inch
                c.setFont("Helvetica", 10)
            c.drawString(inch, y, (user.registration_number if user else '')[:12])
            c.drawString(inch + 1.5 * inch, y, (user.name if user else 'Unknown')[:28])
            c.drawRightString(inch + 4.7 * inch, y, str(attended))
            c.drawRightString(inch + 5.6 * inch, y, str(total_sess))
            c.drawRightString(inch + 6.4 * inch, y, f"{pct}")
            y -= 0.18 * inch
    c.showPage()
    c.save()
    buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='defaulters.pdf')


# ------------------------- RESULTS MANAGEMENT -------------------------

@teacher_bp.route('/teacher/results/manual', methods=['GET', 'POST'])
@teacher_required
def enter_results_manual():
    subjects = Subject.query.filter_by(teacher_id=current_user.id).all()
    students = User.query.filter_by(role='student').all()
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        subject_id = request.form.get('subject_id')
        exam_type = request.form.get('exam_type')
        marks_obtained = request.form.get('marks_obtained')
        max_marks = request.form.get('max_marks')
        remarks = request.form.get('remarks')

        if not all([student_id, subject_id, exam_type, marks_obtained, max_marks]):
            flash('Please fill all required fields.', 'error')
            return render_template('teacher/results_entry.html', subjects=subjects, students=students)

        try:
            marks_obtained = float(marks_obtained)
            max_marks = float(max_marks)
        except ValueError:
            flash('Marks must be numbers.', 'error')
            return render_template('teacher/results_entry.html', subjects=subjects, students=students)

        # Upsert by unique constraint (student_id, subject_id, exam_type)
        existing = Result.query.filter_by(student_id=student_id, subject_id=subject_id, exam_type=exam_type).first()
        if existing:
            existing.marks_obtained = marks_obtained
            existing.max_marks = max_marks
            existing.remarks = remarks
        else:
            res = Result(student_id=student_id, subject_id=subject_id, exam_type=exam_type,
                         marks_obtained=marks_obtained, max_marks=max_marks, remarks=remarks)
            db.session.add(res)
        db.session.commit()
        flash('Result saved successfully.', 'success')
        return redirect(url_for('teacher.enter_results_manual'))

    return render_template('teacher/results_entry.html', subjects=subjects, students=students)


@teacher_bp.route('/teacher/results/upload', methods=['GET', 'POST'])
@teacher_required
def upload_results_csv():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file:
            flash('Please upload a CSV file.', 'error')
            return render_template('teacher/results_upload.html')

        try:
            decoded = file.stream.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(decoded))
        except Exception:
            flash('Invalid file format. Please upload a UTF-8 CSV.', 'error')
            return render_template('teacher/results_upload.html')

        required_cols = {'student_id', 'subject', 'exam_type', 'marks_obtained', 'max_marks', 'remarks'}
        # Allow subject to be subject_id or subject name
        rows_processed = 0
        rows_upserted = 0
        errors = []
        for idx, row in enumerate(reader, start=2):
            rows_processed += 1
            if not required_cols.issubset(set([*row.keys(), 'subject_id'])):
                errors.append(f"Row {idx}: Missing required columns.")
                continue
            try:
                student_id = int(row.get('student_id'))
                subject_name = row.get('subject')
                subject_id = row.get('subject_id')
                if subject_id:
                    subject_id = int(subject_id)
                    subject = Subject.query.get(subject_id)
                else:
                    subject = Subject.query.filter_by(name=subject_name, teacher_id=current_user.id).first()
                if not subject:
                    errors.append(f"Row {idx}: Subject not found.")
                    continue

                if subject.teacher_id != current_user.id:
                    errors.append(f"Row {idx}: You do not teach this subject.")
                    continue

                exam_type = (row.get('exam_type') or '').strip()
                marks_obtained = float(row.get('marks_obtained'))
                max_marks = float(row.get('max_marks'))
                remarks = row.get('remarks')

                existing = Result.query.filter_by(student_id=student_id, subject_id=subject.id, exam_type=exam_type).first()
                if existing:
                    existing.marks_obtained = marks_obtained
                    existing.max_marks = max_marks
                    existing.remarks = remarks
                else:
                    db.session.add(Result(student_id=student_id, subject_id=subject.id, exam_type=exam_type,
                                          marks_obtained=marks_obtained, max_marks=max_marks, remarks=remarks))
                    rows_upserted += 1
            except Exception as e:
                errors.append(f"Row {idx}: {str(e)}")

        db.session.commit()
        flash(f'Processed {rows_processed} rows. Upserted {rows_upserted}. Errors: {len(errors)}', 'success' if not errors else 'warning')
        for err in errors[:10]:
            flash(err, 'error')
        return redirect(url_for('teacher.upload_results_csv'))

    return render_template('teacher/results_upload.html')

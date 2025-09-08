from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from ..models.models import User, db
from werkzeug.security import generate_password_hash
from sqlalchemy import func

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'teacher':
            return redirect(url_for('teacher.dashboard'))
        else:
            return redirect(url_for('student.dashboard'))
        
    if request.method == 'POST':
        identifier = (request.form.get('identifier') or '').strip()  # Email or registration number
        password = request.form.get('password') or ''
        
        # Try to find user by email or registration number
        user = User.query.filter(
            (func.lower(User.email) == identifier.lower()) | (User.registration_number == identifier)
        ).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            if user.role == 'teacher':
                return redirect(next_page or url_for('teacher.dashboard'))
            else:
                return redirect(next_page or url_for('student.dashboard'))
        
        flash('Invalid credentials', 'error')
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        if current_user.role == 'teacher':
            return redirect(url_for('teacher.dashboard'))
        else:
            return redirect(url_for('student.dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        role = request.form.get('role')
        registration_number = request.form.get('registration_number')
        
        if role == 'student':
            year = request.form.get('year')
            division = request.form.get('division')
            if not all([year, division]):
                flash('All fields are required for students', 'error')
                return render_template('auth/register.html')
        
        # Check if user already exists
        if User.query.filter(
            (User.email == email) | (User.registration_number == registration_number)
        ).first():
            flash('User already exists', 'error')
            return render_template('auth/register.html')
            
        user = User(
            email=email,
            name=name,
            registration_number=registration_number,
            role=role
        )
        if role == 'student':
            user.year = year
            user.division = division
            
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

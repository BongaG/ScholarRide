from flask import Blueprint, render_template, request, redirect, flash, session, current_app
from scholar_ride import db, bcrypt, mail
from scholar_ride.models import User
from flask_mail import Message
from flask_login import login_required, current_user
from scholar_ride.models import User, Notification
import random

auth = Blueprint('auth', __name__)


@auth.route('/')
def home():
    if current_user.is_authenticated:
        return redirect('/rides')
    return render_template('index.html')


@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        role = request.form.get('role')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        student_number = request.form.get('student_number')
        staff_number = request.form.get('staff_number')
        driver_number = request.form.get('driver_number')
        department = request.form.get('department')

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return redirect('/register')

        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return redirect('/register')

        if not any(c.isupper() for c in password):
            flash('Password must contain at least one uppercase letter.', 'danger')
            return redirect('/register')

        if not any(c.islower() for c in password):
            flash('Password must contain at least one lowercase letter.', 'danger')
            return redirect('/register')

        if not any(c.isdigit() for c in password):
            flash('Password must contain at least one number.', 'danger')
            return redirect('/register')

        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
            flash('Password must contain at least one special character.', 'danger')
            return redirect('/register')

        if role == 'student' and not email.endswith('@dut4life.ac.za'):
            flash('Students must use their DUT email ending in @dut4life.ac.za', 'danger')
            return redirect('/register')

        if role == 'staff' and not email.endswith('@dut.ac.za'):
            flash('Staff must use their DUT email ending in @dut.ac.za', 'danger')
            return redirect('/register')

        if role == 'driver' and not (email.endswith('@dut4life.ac.za') or email.endswith('@dut.ac.za')):
            flash('Drivers must use a valid DUT email address.', 'danger')
            return redirect('/register')

        if role == 'student':
            if not student_number or not student_number.isdigit() or len(student_number) != 8:
                flash('Student number must be exactly 8 digits.', 'danger')
                return redirect('/register')

        if role == 'staff':
            if not staff_number or not staff_number.upper().startswith('ST') or not staff_number[2:].isdigit():
                flash('Staff number must start with ST followed by numbers e.g. ST00123', 'danger')
                return redirect('/register')

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash('Email already registered.', 'danger')
            return redirect('/register')

        hashed = bcrypt.generate_password_hash(password).decode('utf-8')
        otp = str(random.randint(100000, 999999))

        user = User(
            full_name=full_name,
            email=email,
            phone=phone,
            role=role,
            password_hash=hashed,
            otp=otp,
            verified=False,
            student_number=student_number if role == 'student' else driver_number if role == 'driver' else None,
            staff_number=staff_number if role == 'staff' else None,
            department=department if role == 'staff' else None
        )
        db.session.add(user)
        db.session.commit()

        session['otp_email'] = email

        try:
            msg = Message(
                subject='Scholar-Ride: Your Verification Code',
                sender=current_app.config['MAIL_USERNAME'],
                recipients=[email]
            )
            msg.body = f'Hi {full_name},\n\nYour verification code is: {otp}\n\nEnter this on the verification page to activate your account.\n\n– Scholar-Ride Team'
            mail.send(msg)
            flash('A verification code has been sent to your email.', 'success')
        except Exception as e:
            print(f'EMAIL ERROR: {e}')
            flash(f'Account created but email failed. Your OTP is: {otp}', 'warning')

        return redirect('/verify-otp')

    return render_template('auth/register.html')


@auth.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        entered_otp = request.form.get('otp')
        email = session.get('otp_email')

        user = User.query.filter_by(email=email).first()
        if user and user.otp == entered_otp:
            user.verified = True
            user.otp = None
            db.session.commit()
            flash('Account verified! You can now log in.', 'success')
            return redirect('/login')
        else:
            flash('Invalid OTP. Try again.', 'danger')

    return render_template('auth/verify_otp.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    from flask_login import login_user
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if not user or not bcrypt.check_password_hash(user.password_hash, password):
            flash('Invalid email or password.', 'danger')
            return redirect('/login')

        if not user.verified:
            flash('Please verify your account first.', 'warning')
            session['otp_email'] = email
            return redirect('/verify-otp')

        login_user(user, remember=True)

        unread = Notification.query.filter_by(
            user_id=user.id, is_read=False
        ).count()
        if unread > 0:
            flash(f'You have {unread} unread notification(s). <a href="/notifications">View</a>', 'info')

        flash(f'Welcome back, {user.full_name}!', 'success')
        return redirect('/rides')

    return render_template('auth/login.html')


@auth.route('/logout')
def logout():
    from flask_login import logout_user
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect('/login')


@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()

        if not user:
            flash('No account found with that email.', 'danger')
            return redirect('/forgot-password')

        otp = str(random.randint(100000, 999999))
        user.otp = otp
        db.session.commit()

        session['reset_email'] = email

        try:
            msg = Message(
                subject='Scholar-Ride: Password Reset Code',
                sender=current_app.config['MAIL_USERNAME'],
                recipients=[email]
            )
            msg.body = f'Hi {user.full_name},\n\nYour password reset code is: {otp}\n\nEnter this code to reset your password.\n\n– Scholar-Ride Team'
            mail.send(msg)
            flash('A reset code has been sent to your email.', 'success')
        except Exception as e:
            print(f'EMAIL ERROR: {e}')
            flash(f'Email failed. Your reset code is: {otp}', 'warning')

        return redirect('/reset-password')

    return render_template('auth/forgot_password.html')


@auth.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        entered_otp = request.form.get('otp')
        new_password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        email = session.get('reset_email')

        if not email:
            flash('Session expired. Please try again.', 'danger')
            return redirect('/forgot-password')

        if new_password != confirm:
            flash('Passwords do not match.', 'danger')
            return redirect('/reset-password')

        if len(new_password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return redirect('/reset-password')

        if not any(c.isupper() for c in new_password):
            flash('Password must contain at least one uppercase letter.', 'danger')
            return redirect('/reset-password')

        if not any(c.islower() for c in new_password):
            flash('Password must contain at least one lowercase letter.', 'danger')
            return redirect('/reset-password')

        if not any(c.isdigit() for c in new_password):
            flash('Password must contain at least one number.', 'danger')
            return redirect('/reset-password')

        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in new_password):
            flash('Password must contain at least one special character.', 'danger')
            return redirect('/reset-password')

        user = User.query.filter_by(email=email).first()

        if not user or user.otp != entered_otp:
            flash('Invalid reset code. Try again.', 'danger')
            return redirect('/reset-password')

        user.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
        user.otp = None
        db.session.commit()

        session.pop('reset_email', None)
        flash('Password reset successful! You can now log in.', 'success')
        return redirect('/login')

    return render_template('auth/reset_password.html')


@auth.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        current_user.full_name = full_name
        current_user.phone = phone

        if new_password:
            if new_password != confirm_password:
                flash('Passwords do not match.', 'danger')
                return redirect('/profile')
            current_user.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
            flash('Password updated successfully.', 'success')

        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect('/profile')

    return render_template('profile.html')
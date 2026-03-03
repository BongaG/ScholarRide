from flask import Blueprint, render_template, request, redirect, flash, session, current_app
from scholar_ride import db, bcrypt, mail
from scholar_ride.models import User
from flask_mail import Message
import random

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        student_number = request.form.get('student_number')
        email = request.form.get('email')
        phone = request.form.get('phone')
        role = request.form.get('role')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return redirect('/register')

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash('Email already registered.', 'danger')
            return redirect('/register')

        hashed = bcrypt.generate_password_hash(password).decode('utf-8')
        otp = str(random.randint(100000, 999999))

        user = User(
            full_name=full_name,
            student_number=student_number,
            email=email,
            phone=phone,
            role=role,
            password_hash=hashed,
            otp=otp,
            verified=False
        )
        db.session.add(user)
        db.session.commit()

        session['otp_email'] = email

        # Send OTP email
        try:
            msg = Message(
                subject='Scholar-Ride: Your Verification Code',
                sender=current_app.config['MAIL_USERNAME'],
                recipients=[email]
            )
            msg.body = f'''Hi {full_name},

Your Scholar-Ride verification code is:

    {otp}

Enter this code on the verification page to activate your account.
This code is valid for one use only.

If you did not register on Scholar-Ride, ignore this email.

– Scholar-Ride Team
'''
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

        login_user(user)
        flash(f'Welcome back, {user.full_name}!', 'success')
        return redirect('/rides')

    return render_template('auth/login.html')


@auth.route('/logout')
def logout():
    from flask_login import logout_user
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect('/login')
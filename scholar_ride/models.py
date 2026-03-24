from . import db, login_manager
from flask_login import UserMixin
from datetime import datetime, timedelta

def sast_now():
    return datetime.now()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    student_number = db.Column(db.String(20), unique=True, nullable=True)
    staff_number = db.Column(db.String(20), unique=True, nullable=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='student')
    department = db.Column(db.String(100), nullable=True)
    verified = db.Column(db.Boolean, default=False)
    approval_status = db.Column(db.String(20), default='pending')
    otp = db.Column(db.String(6), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    driver_code = db.Column(db.String(20), nullable=True)

    rides = db.relationship('Ride', backref='driver', lazy=True)
    bookings = db.relationship('Booking', backref='student', lazy=True)
    session_token = db.Column(db.String(100), nullable=True)

class Ride(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    origin = db.Column(db.String(200), nullable=False)
    destination = db.Column(db.String(200), nullable=False)
    departure_time = db.Column(db.DateTime, nullable=False)
    available_seats = db.Column(db.Integer, nullable=False)
    total_seats = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bookings = db.relationship('Booking', backref='ride', lazy=True)
    vehicle_type = db.Column(db.String(50), nullable=True)
    vehicle_model = db.Column(db.String(100), nullable=True)
    registration_number = db.Column(db.String(20), nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ride_id = db.Column(db.Integer, db.ForeignKey('ride.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=sast_now)
class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=sast_now)

class Dispute(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reported_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reported_user = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ride_id = db.Column(db.Integer, db.ForeignKey('ride.id'), nullable=True)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='open')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reported_by_user = db.relationship('User', foreign_keys=[reported_by])
    reported_against_user = db.relationship('User', foreign_keys=[reported_user])

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ride_id = db.Column(db.Integer, db.ForeignKey('ride.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reviewer = db.relationship('User', foreign_keys=[reviewer_id])
    driver = db.relationship('User', foreign_keys=[driver_id])

class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bus_number = db.Column(db.String(20), unique=True, nullable=False)
    registration_number = db.Column(db.String(20), unique=True, nullable=False)
    vehicle_type = db.Column(db.String(50), nullable=False)
    make_model = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='available')
    current_driver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    current_ride_id = db.Column(db.Integer, db.ForeignKey('ride.id'), nullable=True)
    notes = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    current_driver = db.relationship('User', foreign_keys=[current_driver_id])
    current_ride = db.relationship('Ride', foreign_keys=[current_ride_id])


class Inquiry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    reply = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='open')
    created_at = db.Column(db.DateTime, default=sast_now)

    user = db.relationship('User', foreign_keys=[user_id])


class OverflowRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_ride_id = db.Column(db.Integer, db.ForeignKey('ride.id'), nullable=False)
    requesting_student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    reason = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='pending')
    new_ride_id = db.Column(db.Integer, db.ForeignKey('ride.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=sast_now)

    original_ride = db.relationship('Ride', foreign_keys=[original_ride_id])
    new_ride = db.relationship('Ride', foreign_keys=[new_ride_id])
    requesting_student = db.relationship('User', foreign_keys=[requesting_student_id])
from flask import Blueprint, render_template, request, redirect, flash
from flask_login import login_required, current_user
from flask_mail import Message
from flask import current_app
from scholar_ride import db, mail
from datetime import datetime
from scholar_ride.models import User, Ride, Booking, Announcement, Notification, Dispute, Inquiry
import random

admin = Blueprint('admin', __name__)


def send_email(to_email, subject, body):
    try:
        msg = Message(
            subject=subject,
            sender=current_app.config['MAIL_USERNAME'],
            recipients=[to_email]
        )
        msg.body = body
        mail.send(msg)
        return True
    except Exception as e:
        print(f'EMAIL ERROR: {e}')
        return False


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect('/rides')
        return f(*args, **kwargs)
    return decorated


@admin.route('/admin')
@login_required
@admin_required
def dashboard():
    users = User.query.order_by(User.created_at.desc()).all()
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    all_rides = Ride.query.order_by(Ride.created_at.desc()).all()
    disputes = Dispute.query.order_by(Dispute.created_at.desc()).all()
    total_users = User.query.count()
    active_rides = Ride.query.filter_by(status='active').count()
    total_bookings = Booking.query.count()
    total_announcements = Announcement.query.count()
    pending_count = User.query.filter_by(approval_status='pending').count()
    inquiries =Inquiry.query.order_by(Inquiry.created_at.desc()).all()

    return render_template('admin/dashboard.html',
                           users=users,
                           announcements=announcements,
                           all_rides=all_rides,
                           disputes=disputes,
                           total_users=total_users,
                           active_rides=active_rides,
                           total_bookings=total_bookings,
                           total_announcements=total_announcements,
                           pending_count=pending_count,
                           inquiries=inquiries
                           
                           
                           )

@admin.route('/admin/registrations')
@login_required
@admin_required
def pending_registrations():
    pending = User.query.filter_by(approval_status='pending').order_by(User.created_at.desc()).all()
    return render_template('admin/registrations.html', pending=pending)


@admin.route('/admin/users/<int:user_id>/approve')
@login_required
@admin_required
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    user.approval_status = 'approved'

    otp = str(random.randint(100000, 999999))
    user.otp = otp
    db.session.commit()

    notif = Notification(
        user_id=user.id,
        message='✅ Your  registration has been approved' 
    )
    db.session.add(notif)
    db.session.commit()

    sent = send_email(
        user.email,
        'Scholar-Ride: Your Account Has Been Approved',
        f'Hi {user.full_name},\n\nGreat news! Your Scholar-Ride registration has been approved.\n\nYour verification code is: {otp}\n\nGo to the verification page and enter this code to activate your account.\n\n– Scholar-Ride Team'
    )

    if sent:
        flash(f'{user.full_name} approved — OTP sent to {user.email}.', 'success')
    else:
        flash(f'{user.full_name} approved. Email failed — OTP is: {otp}', 'warning')

    return redirect('/admin/registrations')


@admin.route('/admin/users/<int:user_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_user(user_id):
    user = User.query.get_or_404(user_id)
    reason = request.form.get('reason', 'Your registration did not meet the requirement.')
    user.approval_status = 'rejected'
    db.session.commit()

    send_email(
        user.email,
        'Scholar-Ride: Registration Not Approved',
        f'Hi {user.full_name},\n\nUnfortunately your Scholar-Ride registration was not approved.\n\nReason: {reason}\n\nIf you believe this is an error, please contact the administrator.\n\n– Scholar-Ride Team'
    )

    flash(f'{user.full_name} registration rejected.', 'info')
    return redirect('/admin/registrations')


# ── USER MANAGEMENT ───────────────────────────────────────────────────────────

@admin.route('/admin/users/<int:user_id>/toggle')
@login_required
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    user.verified = not user.verified
    db.session.commit()
    flash(f'{user.full_name} has been {"activated" if user.verified else "deactivated"}.', 'success')
    return redirect('/admin')


@admin.route('/admin/users/<int:user_id>/role', methods=['POST'])
@login_required
@admin_required
def change_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role')
    user.role = new_role
    db.session.commit()
    flash(f'{user.full_name} role changed to {new_role}.', 'success')
    return redirect('/admin')


@admin.route('/admin/users/<int:user_id>/delete')
@login_required
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect('/admin')
    user = User.query.get_or_404(user_id)

    Notification.query.filter_by(user_id=user_id).delete()
    Booking.query.filter_by(student_id=user_id).delete()

    rides = Ride.query.filter_by(driver_id=user_id).all()
    for ride in rides:
        Booking.query.filter_by(ride_id=ride.id).delete()
        ride.status = 'cancelled'

    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully.', 'success')
    return redirect('/admin')


# ── RIDE MANAGEMENT ───────────────────────────────────────────────────────────

@admin.route('/admin/rides/<int:ride_id>/cancel')
@login_required
@admin_required
def cancel_ride(ride_id):
    ride = Ride.query.get_or_404(ride_id)
    ride.status = 'cancelled'

    bookings = Booking.query.filter_by(ride_id=ride_id, status='confirmed').all()
    for booking in bookings:
        notif = Notification(
            user_id=booking.student_id,
            message=f'Admin has cancelled the ride from {ride.origin} to {ride.destination}.'
        )
        db.session.add(notif)

    db.session.commit()
    flash('Ride cancelled and all riders notified.', 'success')
    return redirect('/admin')


@admin.route('/admin/rides/<int:ride_id>/delete')
@login_required
@admin_required
def delete_ride(ride_id):
    ride = Ride.query.get_or_404(ride_id)

    bookings = Booking.query.filter_by(ride_id=ride_id, status='confirmed').all()
    for booking in bookings:
        notif = Notification(
            user_id=booking.student_id,
            message=f'A ride from {ride.origin} to {ride.destination} has been removed by admin.'
        )
        db.session.add(notif)

    Booking.query.filter_by(ride_id=ride_id).delete()
    db.session.delete(ride)
    db.session.commit()
    flash('Ride deleted successfully.', 'success')
    return redirect('/admin')




@admin.route('/admin/announcements', methods=['POST'])
@login_required
@admin_required
def post_announcement():
    title = request.form.get('title')
    body = request.form.get('body')
    category = request.form.get('category')

    ann = Announcement(
        admin_id=current_user.id,
        title=title,
        body=body,
        category=category
    )
    db.session.add(ann)

    all_users = User.query.filter_by(verified=True).all()
    for user in all_users:
        notif = Notification(
            user_id=user.id,
            message=f'[{category.upper()}] {title}: {body}'
        )
        db.session.add(notif)

    db.session.commit()
    flash('Announcement posted and all users notified.', 'success')
    return redirect('/admin')


@admin.route('/admin/announcements/<int:ann_id>/delete')
@login_required
@admin_required
def delete_announcement(ann_id):
    ann = Announcement.query.get_or_404(ann_id)
    db.session.delete(ann)
    db.session.commit()
    flash('Announcement deleted.', 'success')
    return redirect('/admin')




@admin.route('/admin/disputes/<int:dispute_id>/resolve', methods=['POST'])
@login_required
@admin_required
def resolve_dispute(dispute_id):
    dispute = Dispute.query.get_or_404(dispute_id)
    action = request.form.get('action')
    dispute.status = 'resolved'

    user = User.query.get(dispute.reported_user)

    if action == 'warn':
        notif = Notification(user_id=user.id, message='⚠️ You have received a warning from admin regarding a dispute.')
        db.session.add(notif)
        flash(f'Warning sent to {user.full_name}.', 'success')

    elif action == 'ban':
        user.verified = False
        notif = Notification(user_id=user.id, message='🚫 Your account has been suspended due to a dispute resolution.')
        db.session.add(notif)
        flash(f'{user.full_name} has been banned.', 'success')

    db.session.commit()
    return redirect('/admin')


@admin.route('/admin/disputes/<int:dispute_id>/delete')
@login_required
@admin_required
def delete_dispute(dispute_id):
    dispute = Dispute.query.get_or_404(dispute_id)
    db.session.delete(dispute)
    db.session.commit()
    flash('Dispute deleted.', 'success')
    return redirect('/admin')



@admin.route('/transport')
@login_required
def transport_feed():
    from scholar_ride.models import Vehicle
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    vehicles = Vehicle.query.order_by(Vehicle.bus_number).all()
    return render_template('transport/feed.html', announcements=announcements, vehicles=vehicles)


# ── ANALYTICS ─────────────────────────────────────────────────────────────────

@admin.route('/admin/analytics')
@login_required
@admin_required
def analytics():
    from scholar_ride.models import Review
    from sqlalchemy import func

    total_users = User.query.count()
    total_rides = Ride.query.count()
    total_bookings = Booking.query.count()
    total_reviews = Review.query.count()
    total_disputes = Dispute.query.count()

    student_count = User.query.filter_by(role='student').count()
    driver_count = User.query.filter_by(role='driver').count()
    staff_count = User.query.filter_by(role='staff').count()
    verified_count = User.query.filter_by(verified=True).count()
    pending_count = User.query.filter_by(approval_status='pending').count()

    active_rides = Ride.query.filter_by(status='active').count()
    completed_rides = Ride.query.filter_by(status='completed').count()
    cancelled_rides = Ride.query.filter_by(status='cancelled').count()
    breakdown_rides = Ride.query.filter(Ride.status.in_(['breakdown', 'delayed'])).count()

    confirmed_bookings = Booking.query.filter_by(status='confirmed').count()
    pending_bookings = Booking.query.filter_by(status='pending').count()
    cancelled_bookings = Booking.query.filter_by(status='cancelled').count()

    top_drivers_raw = db.session.query(
        User,
        func.avg(Review.rating).label('avg_rating'),
        func.count(Ride.id).label('ride_count')
    ).join(Review, Review.driver_id == User.id)\
     .join(Ride, Ride.driver_id == User.id)\
     .group_by(User.id)\
     .order_by(func.avg(Review.rating).desc())\
     .limit(5).all()

    top_drivers = []
    for driver, avg_rating, ride_count in top_drivers_raw:
        driver.avg_rating = round(avg_rating, 1)
        driver.ride_count = ride_count
        top_drivers.append(driver)

    popular_routes = db.session.query(
        Ride.origin,
        Ride.destination,
        func.count(Ride.id).label('count')
    ).group_by(Ride.origin, Ride.destination)\
     .order_by(func.count(Ride.id).desc())\
     .limit(5).all()

    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()

    return render_template('admin/analytics.html',
        total_users=total_users,
        total_rides=total_rides,
        total_bookings=total_bookings,
        total_reviews=total_reviews,
        total_disputes=total_disputes,
        student_count=student_count,
        driver_count=driver_count,
        staff_count=staff_count,
        verified_count=verified_count,
        pending_count=pending_count,
        active_rides=active_rides,
        completed_rides=completed_rides,
        cancelled_rides=cancelled_rides,
        breakdown_rides=breakdown_rides,
        confirmed_bookings=confirmed_bookings,
        pending_bookings=pending_bookings,
        cancelled_bookings=cancelled_bookings,
        top_drivers=top_drivers,
        popular_routes=popular_routes,
        recent_users=recent_users
    )


# ── DATABASE VIEWER ───────────────────────────────────────────────────────────

@admin.route('/admin/database')
@login_required
@admin_required
def database_viewer():
    from scholar_ride.models import Review

    users = User.query.order_by(User.created_at.desc()).all()
    rides = Ride.query.order_by(Ride.created_at.desc()).all()
    bookings = Booking.query.order_by(Booking.booking_date.desc()).all()
    reviews = Review.query.order_by(Review.created_at.desc()).all()
    disputes = Dispute.query.order_by(Dispute.created_at.desc()).all()
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()

    return render_template('admin/database.html',
        users=users,
        rides=rides,
        bookings=bookings,
        reviews=reviews,
        disputes=disputes,
        announcements=announcements
    )


@admin.route('/admin/fleet')
@login_required
def fleet():
    if current_user.role not in ['admin', 'driver']:
        flash('Not authorised.', 'danger')
        return redirect('/rides')
    from scholar_ride.models import Vehicle
    vehicles = Vehicle.query.order_by(Vehicle.bus_number).all()
    return render_template('admin/fleet.html', vehicles=vehicles)


@admin.route('/admin/fleet/add', methods=['GET', 'POST'])
@login_required
def add_vehicle():
    if current_user.role != 'admin':
        flash('Not authorised.', 'danger')
        return redirect('/rides')
    from scholar_ride.models import Vehicle
    if request.method == 'POST':
        bus_number = request.form.get('bus_number')
        registration_number = request.form.get('registration_number')
        vehicle_type = request.form.get('vehicle_type')
        make_model = request.form.get('make_model')
        capacity = int(request.form.get('capacity'))
        notes = request.form.get('notes')

        existing = Vehicle.query.filter_by(bus_number=bus_number).first()
        if existing:
            flash('Bus number already exists.', 'danger')
            return redirect('/admin/fleet/add')

        vehicle = Vehicle(
            bus_number=bus_number,
            registration_number=registration_number,
            vehicle_type=vehicle_type,
            make_model=make_model,
            capacity=capacity,
            notes=notes
        )
        db.session.add(vehicle)
        db.session.commit()
        flash(f'Vehicle {bus_number} added to fleet!', 'success')
        return redirect('/admin/fleet')

    return render_template('admin/add_vehicle.html')


@admin.route('/admin/fleet/<int:vehicle_id>/status', methods=['POST'])
@login_required
def update_vehicle_status(vehicle_id):
    if current_user.role != 'admin':
        flash('Not authorised.', 'danger')
        return redirect('/rides')
    from scholar_ride.models import Vehicle
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    new_status = request.form.get('status')
    vehicle.status = new_status
    if new_status == 'available':
        vehicle.current_driver_id = None
        vehicle.current_ride_id = None
    db.session.commit()
    flash(f'Vehicle {vehicle.bus_number} status updated to {new_status}.', 'success')
    return redirect('/admin/fleet')


@admin.route('/admin/fleet/<int:vehicle_id>/delete', methods=['POST'])
@login_required
def delete_vehicle(vehicle_id):
    if current_user.role != 'admin':
        flash('Not authorised.', 'danger')
        return redirect('/rides')
    from scholar_ride.models import Vehicle
    vehicle = Vehicle.query.get_or_404(vehicle_id)
    db.session.delete(vehicle)
    db.session.commit()
    flash('Vehicle removed from fleet.', 'success')
    return redirect('/admin/fleet')

@admin.route('/admin/fleet/<int:vehicle_id>/take', methods=['GET', 'POST'])
@login_required
def take_vehicle(vehicle_id):
    if current_user.role != 'driver':
        flash('Only drivers can take vehicles.', 'danger')
        return redirect('/admin/fleet')
    
    from scholar_ride.models import Vehicle
    vehicle = Vehicle.query.get_or_404(vehicle_id)

    if vehicle.status != 'available':
        flash('This vehicle is not available.', 'danger')
        return redirect('/admin/fleet')
    
    active_ride = Ride.query.filter_by(
        driver_id=current_user.id,
        status='active'
    ).first()
    if active_ride:
        flash('You already have an active ride. Complete or cancel it before taking another vehicle.', 'warning')
        return redirect('/admin/fleet')

    if request.method == 'POST':
        origin = request.form.get('origin')
        destination = request.form.get('destination')
        departure_date = request.form.get('departure_date')
        departure_time = request.form.get('departure_time')

        departure_dt = datetime.strptime(
            f'{departure_date} {departure_time}', '%Y-%m-%d %H:%M'
        )

        ride = Ride(
            driver_id=current_user.id,
            origin=origin,
            destination=destination,
            departure_time=departure_dt,
            available_seats=vehicle.capacity,
            total_seats=vehicle.capacity,
            vehicle_type=vehicle.vehicle_type,
            vehicle_model=vehicle.make_model,
            registration_number=vehicle.registration_number
        )
        db.session.add(ride)
        db.session.flush()

        vehicle.status = 'on_trip'
        vehicle.current_driver_id = current_user.id
        vehicle.current_ride_id = ride.id
        db.session.commit()

        admins = User.query.filter_by(role='admin').all()
        for admin_user in admins:
            notif = Notification(
                user_id=admin_user.id,
                message=f'🚌 Driver {current_user.full_name} has taken {vehicle.bus_number} ({vehicle.registration_number}) from {origin} to {destination} — Departure {departure_dt.strftime("%H:%M")}'
            )
            db.session.add(notif)
        db.session.commit()

        flash(f'Ride posted! You have taken {vehicle.bus_number}.', 'success')
        return redirect(f'/rides/{ride.id}')

    return render_template('admin/take_vehicle.html', vehicle=vehicle)



@admin.route('/inquiries/submit', methods=['POST'])
@login_required
def submit_inquiry():
    from scholar_ride.models import Inquiry
    subject = request.form.get('subject')
    message = request.form.get('message')

    inquiry = Inquiry(
        user_id=current_user.id,
        subject=subject,
        message=message
    )
    db.session.add(inquiry)

    admins = User.query.filter_by(role='admin').all()
    for admin_user in admins:
        notif = Notification(
            user_id=admin_user.id,
            message=f'💬 New inquiry from {current_user.full_name}: {subject}'
        )
        db.session.add(notif)
    db.session.commit()

    flash('Your message has been sent to admin!', 'success')
    return redirect(request.referrer or '/rides')


@admin.route('/inquiries/<int:inquiry_id>/reply', methods=['POST'])
@login_required
@admin_required
def reply_inquiry(inquiry_id):
    from scholar_ride.models import Inquiry
    inquiry = Inquiry.query.get_or_404(inquiry_id)
    reply = request.form.get('reply')

    inquiry.reply = reply
    inquiry.status = 'resolved'

    notif = Notification(
        user_id=inquiry.user_id,
        message=f'💬 Admin replied to your inquiry "{inquiry.subject}": {reply}'
    )
    db.session.add(notif)
    db.session.commit()

    flash('Reply sent!', 'success')
    return redirect('/admin')


@admin.route('/inquiries/<int:inquiry_id>/delete')
@login_required
@admin_required
def delete_inquiry(inquiry_id):
    from scholar_ride.models import Inquiry
    inquiry = Inquiry.query.get_or_404(inquiry_id)
    db.session.delete(inquiry)
    db.session.commit()
    flash('Inquiry deleted.', 'success')
    return redirect('/admin')
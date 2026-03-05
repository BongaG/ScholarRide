from flask import Blueprint, render_template, request, redirect, flash
from flask_login import login_required, current_user
from scholar_ride import db
from scholar_ride.models import User, Ride, Booking, Announcement, Notification, Dispute

admin = Blueprint('admin', __name__)

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
    announcements = Announcement.query.order_by(
        Announcement.created_at.desc()).all()
    all_rides = Ride.query.order_by(Ride.created_at.desc()).all()
    disputes = Dispute.query.order_by(Dispute.created_at.desc()).all()
    total_users = User.query.count()
    active_rides = Ride.query.filter_by(status='active').count()
    total_bookings = Booking.query.count()
    total_announcements = Announcement.query.count()

    return render_template('admin/dashboard.html',
                           users=users,
                           announcements=announcements,
                           all_rides=all_rides,
                           disputes=disputes,
                           total_users=total_users,
                           active_rides=active_rides,
                           total_bookings=total_bookings,
                           total_announcements=total_announcements)


# ── USER MANAGEMENT ──────────────────────────────────────────────────────────

@admin.route('/admin/users/<int:user_id>/toggle')
@login_required
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    user.verified = not user.verified
    db.session.commit()
    flash(f'{user.full_name} has been {"activated" if user.verified else "deactivated"}.', 'success')
    return redirect('/admin#users')


@admin.route('/admin/users/<int:user_id>/role', methods=['POST'])
@login_required
@admin_required
def change_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role')
    user.role = new_role
    db.session.commit()
    flash(f'{user.full_name} role changed to {new_role}.', 'success')
    return redirect('/admin#users')


@admin.route('/admin/users/<int:user_id>/delete')
@login_required
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect('/admin#users')
    user = User.query.get_or_404(user_id)

    # Delete all related records first
    Notification.query.filter_by(user_id=user_id).delete()
    Booking.query.filter_by(student_id=user_id).delete()

    # Cancel rides posted by this user
    rides = Ride.query.filter_by(driver_id=user_id).all()
    for ride in rides:
        Booking.query.filter_by(ride_id=ride.id).delete()
        ride.status = 'cancelled'

    db.session.delete(user)
    db.session.commit()
    flash(f'User deleted successfully.', 'success')
    return redirect('/admin#users')


# ── RIDE MANAGEMENT ───────────────────────────────────────────────────────────

@admin.route('/admin/rides/<int:ride_id>/cancel')
@login_required
@admin_required
def cancel_ride(ride_id):
    ride = Ride.query.get_or_404(ride_id)
    ride.status = 'cancelled'

    # Notify all confirmed riders
    bookings = Booking.query.filter_by(ride_id=ride_id, status='confirmed').all()
    for booking in bookings:
        msg = f'Admin has cancelled the ride from {ride.origin} to {ride.destination}.'
        notif = Notification(user_id=booking.student_id, message=msg)
        db.session.add(notif)

    db.session.commit()
    flash('Ride cancelled and all riders notified.', 'success')
    return redirect('/admin#rides')


@admin.route('/admin/rides/<int:ride_id>/delete')
@login_required
@admin_required
def delete_ride(ride_id):
    ride = Ride.query.get_or_404(ride_id)

    # Notify all confirmed riders
    bookings = Booking.query.filter_by(ride_id=ride_id, status='confirmed').all()
    for booking in bookings:
        msg = f'A ride from {ride.origin} to {ride.destination} has been removed by admin.'
        notif = Notification(user_id=booking.student_id, message=msg)
        db.session.add(notif)

    Booking.query.filter_by(ride_id=ride_id).delete()
    db.session.delete(ride)
    db.session.commit()
    flash('Ride deleted successfully.', 'success')
    return redirect('/admin#rides')


# ── ANNOUNCEMENTS ─────────────────────────────────────────────────────────────

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

    # Notify all verified users
    all_users = User.query.filter_by(verified=True).all()
    for user in all_users:
        notif = Notification(
            user_id=user.id,
            message=f'[{category.upper()}] {title}: {body}'
        )
        db.session.add(notif)

    db.session.commit()
    flash('Announcement posted and all users notified.', 'success')
    return redirect('/admin#announcements')


@admin.route('/admin/announcements/<int:ann_id>/delete')
@login_required
@admin_required
def delete_announcement(ann_id):
    ann = Announcement.query.get_or_404(ann_id)
    db.session.delete(ann)
    db.session.commit()
    flash('Announcement deleted.', 'success')
    return redirect('/admin#announcements')


# ── DISPUTES ──────────────────────────────────────────────────────────────────

@admin.route('/admin/disputes/<int:dispute_id>/resolve', methods=['POST'])
@login_required
@admin_required
def resolve_dispute(dispute_id):
    dispute = Dispute.query.get_or_404(dispute_id)
    action = request.form.get('action')
    dispute.status = 'resolved'

    if action == 'warn':
        user = User.query.get(dispute.reported_user)
        msg = f'You have received a warning from admin regarding a dispute.'
        notif = Notification(user_id=user.id, message=msg)
        db.session.add(notif)
        flash(f'Warning sent to {user.full_name}.', 'success')

    elif action == 'ban':
        user = User.query.get(dispute.reported_user)
        user.verified = False
        msg = f'Your account has been suspended due to a dispute resolution.'
        notif = Notification(user_id=user.id, message=msg)
        db.session.add(notif)
        flash(f'{user.full_name} has been banned.', 'success')

    db.session.commit()
    return redirect('/admin#disputes')


@admin.route('/admin/disputes/<int:dispute_id>/delete')
@login_required
@admin_required
def delete_dispute(dispute_id):
    dispute = Dispute.query.get_or_404(dispute_id)
    db.session.delete(dispute)
    db.session.commit()
    flash('Dispute deleted.', 'success')
    return redirect('/admin#disputes')


# ── TRANSPORT FEED ────────────────────────────────────────────────────────────

@admin.route('/transport')
@login_required
def transport_feed():
    announcements = Announcement.query.order_by(
        Announcement.created_at.desc()).all()
    return render_template('transport/feed.html', announcements=announcements)


@admin.route('/admin/analytics')
@login_required
@admin_required
def analytics():
    from scholar_ride.models import Review, Dispute
    from sqlalchemy import func

    total_users = User.query.count()
    total_rides = Ride.query.count()
    total_bookings = Booking.query.count()
    total_reviews = Review.query.count()
    total_disputes = Dispute.query.count()

    student_count = User.query.filter_by(role='student').count()
    driver_count = User.query.filter_by(role='driver').count()
    verified_count = User.query.filter_by(verified=True).count()

    active_rides = Ride.query.filter_by(status='active').count()
    completed_rides = Ride.query.filter_by(status='completed').count()
    cancelled_rides = Ride.query.filter_by(status='cancelled').count()
    breakdown_rides = Ride.query.filter(
        Ride.status.in_(['breakdown', 'delayed'])
    ).count()

    confirmed_bookings = Booking.query.filter_by(status='confirmed').count()
    pending_bookings = Booking.query.filter_by(status='pending').count()
    cancelled_bookings = Booking.query.filter_by(status='cancelled').count()

    # Top drivers by average rating
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

    # Popular routes
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
        verified_count=verified_count,
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
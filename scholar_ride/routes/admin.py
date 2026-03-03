from flask import Blueprint, render_template, request, redirect, flash
from flask_login import login_required, current_user
from scholar_ride import db
from scholar_ride.models import User, Ride, Booking, Announcement, Notification

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
        Announcement.created_at.desc()
    ).limit(10).all()
    total_users = User.query.count()
    active_rides = Ride.query.filter_by(status='active').count()
    total_bookings = Booking.query.count()
    total_announcements = Announcement.query.count()

    return render_template('admin/dashboard.html',
                           users=users,
                           announcements=announcements,
                           total_users=total_users,
                           active_rides=active_rides,
                           total_bookings=total_bookings,
                           total_announcements=total_announcements)

@admin.route('/admin/users/<int:user_id>/toggle')
@login_required
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    user.verified = not user.verified
    db.session.commit()
    flash(f'{user.full_name} has been {"activated" if user.verified else "deactivated"}.', 'success')
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

    # Notify all users
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

@admin.route('/transport')
@login_required
def transport_feed():
    announcements = Announcement.query.order_by(
        Announcement.created_at.desc()
    ).all()
    return render_template('transport/feed.html', announcements=announcements)
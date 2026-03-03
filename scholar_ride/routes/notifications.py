from flask import Blueprint, render_template
from flask_login import login_required, current_user
from scholar_ride import db
from scholar_ride.models import Notification

notifications = Blueprint('notifications', __name__)

@notifications.route('/notifications')
@login_required
def index():
    notifs = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.created_at.desc()).all()

    # Mark all as read
    for n in notifs:
        n.is_read = True
    db.session.commit()

    return render_template('notifications.html', notifications=notifs)
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from scholar_ride import db
from scholar_ride.models import Notification
from datetime import datetime, timedelta

notifications = Blueprint('notifications', __name__)

@notifications.route('/notifications')
@login_required
def index():
    selected_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    query = Notification.query.filter_by(user_id=current_user.id)

    if selected_date:
        try:
            day = datetime.strptime(selected_date, '%Y-%m-%d')
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.filter(
                Notification.created_at >= day_start,
                Notification.created_at <= day_end
            )
        except ValueError:
            pass

    notifs = query.order_by(Notification.created_at.desc()).all()

    for n in notifs:
        n.is_read = True
    db.session.commit()

    return render_template('notifications.html', notifications=notifs, selected_date=selected_date)
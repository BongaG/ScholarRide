from scholar_ride import create_app, db
from scholar_ride.models import User

app = create_app()
with app.app_context():
    admins = User.query.filter_by(role='admin').all()
    for a in admins:
        a.approval_status = 'approved'
        a.verified = True
    db.session.commit()
    print('Done - all admins fixed')
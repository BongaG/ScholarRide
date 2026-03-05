from scholar_ride import create_app, db
from scholar_ride.models import User, Notification, Booking

app = create_app()
with app.app_context():
    user = User.query.filter_by(email='22202467@dut4life.ac.za').first()
    if user:
        Notification.query.filter_by(user_id=user.id).delete()
        Booking.query.filter_by(student_id=user.id).delete()
        db.session.delete(user)
        db.session.commit()
        print('User deleted successfully')
    else:
        print('User not found')
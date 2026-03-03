from scholar_ride import create_app, db
from scholar_ride.models import User

app = create_app()
with app.app_context():
    user = User.query.filter_by(email='22202467@dut4life.ac.za').first()
    if user:
        user.role = 'admin'
        db.session.commit()
        print('Done! Role is now:', user.role)
    else:
        print('User not found')
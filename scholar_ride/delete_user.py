from scholar_ride import create_app, db
from scholar_ride.models import User

app = create_app()
with app.app_context():
    User.query.delete()
    db.session.commit()
    print('All users deleted')
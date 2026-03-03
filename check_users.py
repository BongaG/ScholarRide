from scholar_ride import create_app, db
from scholar_ride.models import User

app = create_app()
with app.app_context():
    users = User.query.all()
    for user in users:
        print(f'ID: {user.id} | Name: {user.full_name} | Email: {user.email} | Role: {user.role}')
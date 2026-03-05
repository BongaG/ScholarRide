from scholar_ride import create_app, db
from scholar_ride.models import User

app = create_app()
with app.app_context():
    users = User.query.all()
    for user in users:
        print(f'ID: {user.id} | Name: {user.full_name} | Email: {user.email} | Role: {user.role} | Verified: {user.verified}')
    
    # Force verify and make admin the first user
    user = User.query.filter_by(email='bongagazu10@gmail.com').first()
    if user:
        user.verified = True
        user.role = 'admin'
        db.session.commit()
        print('\nFixed! bongagazu10@gmail.com is now verified admin')
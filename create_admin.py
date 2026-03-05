from scholar_ride import create_app, db
from scholar_ride.models import User
from scholar_ride import bcrypt

app = create_app()
with app.app_context():
    existing = User.query.filter_by(email='bongagazu10@gmail.com').first()
    if existing:
        existing.role = 'admin'
        existing.verified = True
        existing.password_hash = bcrypt.generate_password_hash('Admin123').decode('utf-8')
        db.session.commit()
        print('Admin updated!')
    else:
        hashed = bcrypt.generate_password_hash('Admin123').decode('utf-8')
        admin = User(
            full_name='Bonga Gazu',
            student_number=None,
            staff_number='ADMIN001',
            email='bongagazu10@gmail.com',
            phone='0000000000',
            password_hash=hashed,
            role='admin',
            verified=True
        )
        db.session.add(admin)
        db.session.commit()
        print('Admin created!')
    
    print('Email: bongagazu10@gmail.com')
    print('Password: Admin123')
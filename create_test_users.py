from scholar_ride import create_app, db
from scholar_ride.models import User
from scholar_ride import bcrypt

app = create_app()
with app.app_context():
    # Test Driver
    existing_driver = User.query.filter_by(email='testdriver@dut4life.ac.za').first()
    if not existing_driver:
        driver = User(
            full_name='Test Driver',
            student_number='11111111',
            email='testdriver@dut4life.ac.za',
            phone='0731234567',
            password_hash=bcrypt.generate_password_hash('Test@1234').decode('utf-8'),
            role='driver',
            verified=True
        )
        db.session.add(driver)
        print('Driver created')

    # Test Student
    existing_student = User.query.filter_by(email='teststudent@dut4life.ac.za').first()
    if not existing_student:
        student = User(
            full_name='Test Student',
            student_number='22222222',
            email='teststudent@dut4life.ac.za',
            phone='0739876543',
            password_hash=bcrypt.generate_password_hash('Test@1234').decode('utf-8'),
            role='student',
            verified=True
        )
        db.session.add(student)
        print('Student created')

    # Test Staff
    existing_staff = User.query.filter_by(email='teststaff@dut.ac.za').first()
    if not existing_staff:
        staff = User(
            full_name='Test Staff',
            staff_number='ST00999',
            email='teststaff@dut.ac.za',
            phone='0712345678',
            password_hash=bcrypt.generate_password_hash('Test@1234').decode('utf-8'),
            role='staff',
            verified=True,
            department='Information Technology'
        )
        db.session.add(staff)
        print('Staff created')

    db.session.commit()
    print('All test users ready!')
    print('Password for all: Test@1234')
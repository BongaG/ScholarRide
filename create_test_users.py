from scholar_ride import create_app, db
from scholar_ride.models import User
from scholar_ride import bcrypt

app = create_app()
with app.app_context():

    users = [
        # Drivers
        {'full_name': 'Test Driver', 'student_number': '11111111', 'email': 'testdriver@dut4life.ac.za', 'phone': '0731234567', 'role': 'driver', 'staff_number': None, 'department': None},
        {'full_name': 'Driver Two', 'student_number': '11111112', 'email': 'testdriver2@dut4life.ac.za', 'phone': '0731234568', 'role': 'driver', 'staff_number': None, 'department': None},
        {'full_name': 'Driver Three', 'student_number': '11111113', 'email': 'testdriver3@dut4life.ac.za', 'phone': '0731234569', 'role': 'driver', 'staff_number': None, 'department': None},

        # Students
        {'full_name': 'Test Student', 'student_number': '22222222', 'email': 'teststudent@dut4life.ac.za', 'phone': '0739876543', 'role': 'student', 'staff_number': None, 'department': None},
        {'full_name': 'Student Two', 'student_number': '22222223', 'email': 'teststudent2@dut4life.ac.za', 'phone': '0739876544', 'role': 'student', 'staff_number': None, 'department': None},
        {'full_name': 'Student Three', 'student_number': '22222224', 'email': 'teststudent3@dut4life.ac.za', 'phone': '0739876545', 'role': 'student', 'staff_number': None, 'department': None},

        # Staff
        {'full_name': 'Test Staff', 'student_number': None, 'email': 'teststaff@dut.ac.za', 'phone': '0712345678', 'role': 'staff', 'staff_number': 'ST00999', 'department': 'Information Technology'},
        {'full_name': 'Staff Two', 'student_number': None, 'email': 'teststaff2@dut.ac.za', 'phone': '0712345679', 'role': 'staff', 'staff_number': 'ST01000', 'department': 'Engineering'},
        {'full_name': 'Staff Three', 'student_number': None, 'email': 'teststaff3@dut.ac.za', 'phone': '0712345680', 'role': 'staff', 'staff_number': 'ST01001', 'department': 'Business'},
    ]

    for u in users:
        existing = User.query.filter_by(email=u['email']).first()
        if not existing:
            user = User(
                full_name=u['full_name'],
                student_number=u['student_number'],
                staff_number=u['staff_number'],
                email=u['email'],
                phone=u['phone'],
                password_hash=bcrypt.generate_password_hash('Test@1234').decode('utf-8'),
                role=u['role'],
                verified=True,
                approval_status='approved',
                department=u['department']
            )
            db.session.add(user)
            print(f'{u["role"].upper()} created: {u["email"]}')

    db.session.commit()
    print('All test users ready!')
    print('Password for all: Test@1234')
from scholar_ride import create_app, db
from scholar_ride.models import Vehicle

app = create_app()
with app.app_context():

    vehicles = [
        {'bus_number': 'DUT-100', 'registration_number': 'ND 123 GP', 'vehicle_type': 'Bus', 'make_model': 'Toyota Coaster', 'capacity': 65},
        {'bus_number': 'DUT-101', 'registration_number': 'ND 456 GP', 'vehicle_type': 'Bus', 'make_model': 'Hino 500', 'capacity': 65},
        {'bus_number': 'DUT-102', 'registration_number': 'ND 789 GP', 'vehicle_type': 'Bus', 'make_model': 'Mercedes Benz Sprinter', 'capacity': 65},
        {'bus_number': 'DUT-103', 'registration_number': 'ND 321 KZ', 'vehicle_type': 'Minibus', 'make_model': 'Toyota Quantum', 'capacity': 15},
        {'bus_number': 'DUT-104', 'registration_number': 'ND 654 KZ', 'vehicle_type': 'Minibus', 'make_model': 'Toyota Quantum', 'capacity': 15},
        {'bus_number': 'DUT-105', 'registration_number': 'ND 987 KZ', 'vehicle_type': 'Minibus', 'make_model': 'Nissan NV350', 'capacity': 15},
        {'bus_number': 'DUT-106', 'registration_number': 'ND 111 KZ', 'vehicle_type': 'Minibus', 'make_model': 'Ford Transit', 'capacity': 15},
        {'bus_number': 'DUT-107', 'registration_number': 'ND 222 KZ', 'vehicle_type': 'Car', 'make_model': 'Toyota Corolla', 'capacity': 4},
        {'bus_number': 'DUT-108', 'registration_number': 'ND 333 KZ', 'vehicle_type': 'Car', 'make_model': 'VW Polo', 'capacity': 4},
        {'bus_number': 'DUT-109', 'registration_number': 'ND 444 KZ', 'vehicle_type': 'Car', 'make_model': 'Toyota Fortuner', 'capacity': 4},
        {'bus_number': 'DUT-110', 'registration_number': 'ND 555 KZ', 'vehicle_type': 'Car', 'make_model': 'Hyundai Tucson', 'capacity': 4},
    ]

    for v in vehicles:
        existing = Vehicle.query.filter_by(bus_number=v['bus_number']).first()
        if not existing:
            vehicle = Vehicle(
                bus_number=v['bus_number'],
                registration_number=v['registration_number'],
                vehicle_type=v['vehicle_type'],
                make_model=v['make_model'],
                capacity=v['capacity'],
                status='available'
            )
            db.session.add(vehicle)
            print(f"Added {v['bus_number']} — {v['vehicle_type']} — {v['make_model']}")
        else:
            print(f"Skipped {v['bus_number']} — already exists")

    db.session.commit()
    print('Fleet created!')
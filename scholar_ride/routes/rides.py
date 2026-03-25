from flask import Blueprint, render_template, request, redirect, flash
from flask_login import login_required, current_user
from scholar_ride import db
from scholar_ride.models import Ride, Booking
from datetime import datetime, timedelta
from scholar_ride.models import Ride, Booking, Notification, User


rides = Blueprint('rides', __name__)



@rides.route('/rides')
@login_required
def index():
    origin = request.args.get('origin', '')
    destination = request.args.get('destination', '')
    date = request.args.get('date', '')

    query = Ride.query.filter(Ride.status.in_(['active', 'delayed']))

    if origin:
        query = query.filter(Ride.origin.ilike(f'%{origin}%'))
    if destination:
        query = query.filter(Ride.destination.ilike(f'%{destination}%'))
    if date:
        try:
            search_date = datetime.strptime(date, '%Y-%m-%d')
            query = query.filter(
                db.func.date(Ride.departure_time) == search_date.date()
            )
        except:
            pass

    all_rides = query.order_by(Ride.departure_time.asc()).all()
    return render_template('rides/index.html', rides=all_rides)


@rides.route('/rides/post', methods=['GET', 'POST'])
@login_required
def post_ride():
    if current_user.role == 'driver':
        flash('Drivers must post rides through the Fleet.', 'warning')
        return redirect('/admin/fleet')

    if request.method == 'POST':
        origin = request.form.get('origin')
        destination = request.form.get('destination')
        departure_date = request.form.get('departure_date')
        departure_time = request.form.get('departure_time')
        seats = int(request.form.get('seats'))
        vehicle_type = request.form.get('vehicle_type')
        vehicle_model = request.form.get('vehicle_model')
        registration_number = request.form.get('registration_number')
        bus_number=request.form.get('bus_number')

        departure_dt = datetime.strptime(
            f'{departure_date} {departure_time}', '%Y-%m-%d %H:%M'
        )

        ride = Ride(
            driver_id=current_user.id,
            origin=origin,
            destination=destination,
            departure_time=departure_dt,
            available_seats=seats,
            total_seats=seats,
            vehicle_type=vehicle_type,
            vehicle_model=vehicle_model,
            registration_number=registration_number,
            bus_number=bus_number
        )
        db.session.add(ride)
        db.session.commit()

        flash('Ride posted successfully!', 'success')
        return redirect('/rides')

    return render_template('rides/post.html')


@rides.route('/rides/my')
@login_required
def my_rides():
    all_rides = Ride.query.filter_by(
        driver_id=current_user.id
    ).order_by(Ride.departure_time.desc()).all()
    return render_template('rides/my_rides.html', rides=all_rides)


@rides.route('/rides/<int:ride_id>')
@login_required
def ride_detail(ride_id):
    from scholar_ride.models import OverflowRequest
    ride = Ride.query.get_or_404(ride_id)
    bookings = Booking.query.filter_by(ride_id=ride_id).all()

    already_booked = False
    booking_status = None
    if current_user.role in ['student', 'staff']:
        existing = Booking.query.filter_by(
            ride_id=ride_id, student_id=current_user.id
        ).first()
        if existing:
            already_booked = True
            booking_status = existing.status

    overflow_pending = OverflowRequest.query.filter_by(
        original_ride_id=ride_id,
        status='pending'
    ).first() is not None
    dispute_count = 0
    if current_user.role in ['student', 'staff']:
        from scholar_ride.models import Dispute
        dispute_count = Dispute.query.filter_by(
            reported_by=current_user.id,
            ride_id=ride_id
        ).count()

    return render_template('rides/detail.html',
                           ride=ride,
                           bookings=bookings,
                           already_booked=already_booked,
                           booking_status=booking_status,
                           overflow_pending=overflow_pending,
                           dispute_count=dispute_count)

@rides.route('/rides/<int:ride_id>/update', methods=['POST'])
@login_required
def update_ride(ride_id):
    ride = Ride.query.get_or_404(ride_id)

    if current_user.id != ride.driver_id:
        flash('Not authorised.', 'danger')
        return redirect(f'/rides/{ride_id}')

    new_status = request.form.get('status')
    ride.status = new_status
    if new_status == 'completed':
        from datetime import datetime
        ride.completed_at = datetime.now()
    db.session.commit()

    if new_status in ['cancelled', 'delayed', 'breakdown', 'completed']:
        from scholar_ride.models import Notification
        bookings = Booking.query.filter_by(
            ride_id=ride_id, status='confirmed'
        ).all()
        for booking in bookings:
            if new_status == 'completed':
                msg = f'✅ Your ride from {ride.origin} to {ride.destination} has been completed. Thank you for riding with Scholar-Ride!'
            elif new_status == 'cancelled':
                msg = f'❌ Your ride from {ride.origin} to {ride.destination} has been cancelled.'
            elif new_status == 'delayed':
                msg = f'⏳ Your ride from {ride.origin} to {ride.destination} has been delayed.'
            elif new_status == 'breakdown':
                msg = f'🚨 Your ride from {ride.origin} to {ride.destination} has a breakdown.'
            notif = Notification(user_id=booking.student_id, message=msg)
            db.session.add(notif)
        db.session.commit()

    if new_status in ['cancelled', 'delayed', 'breakdown']:
        from scholar_ride.models import Notification
        bookings = Booking.query.filter_by(
            ride_id=ride_id, status='confirmed'
        ).all()
        for booking in bookings:
            msg = f'Your ride from {ride.origin} to {ride.destination} has been marked as {new_status.upper()}.'
            notif = Notification(user_id=booking.student_id, message=msg)
            db.session.add(notif)
        db.session.commit()

    if new_status in ['completed', 'cancelled']:
        from scholar_ride.models import Vehicle
        vehicle = Vehicle.query.filter_by(current_ride_id=ride.id).first()
        if vehicle:
            vehicle.status = 'available'
            vehicle.current_driver_id = None
            vehicle.current_ride_id = None
            db.session.commit()

    if new_status == 'breakdown':
        from scholar_ride.models import Vehicle, OverflowRequest
        
        vehicle = Vehicle.query.filter_by(current_ride_id=ride.id).first()
        if vehicle:
            vehicle.status = 'maintenance'
            vehicle.current_driver_id = None
            vehicle.current_ride_id = None
            db.session.commit()

        
        existing = OverflowRequest.query.filter_by(
            original_ride_id=ride.id,
            status='pending'
        ).first()

        if not existing:
            
            replacement = Vehicle.query.filter_by(
                status='available',
                vehicle_type=ride.vehicle_type
            ).filter(Vehicle.capacity >= ride.total_seats).first()

            if replacement:
                overflow = OverflowRequest(
                    original_ride_id=ride.id,
                    reason='breakdown'
                )
                db.session.add(overflow)
                db.session.flush()

                
                drivers = User.query.filter_by(role='driver').all()
                for driver in drivers:
                    notif = Notification(
                        user_id=driver.id,
                        message=f'🚨 OVERFLOW|{overflow.id}|Emergency! Bus broke down on {ride.origin} → {ride.destination}. Vehicle {replacement.bus_number} ({replacement.registration_number}) is available for you to take.'
                    )
                    db.session.add(notif)

                
                admins = User.query.filter_by(role='admin').all()
                for admin_user in admins:
                    notif = Notification(
                        user_id=admin_user.id,
                        message=f'🚨 Breakdown on {ride.origin} → {ride.destination}. Replacement {replacement.bus_number} dispatched to drivers.'
                    )
                    db.session.add(notif)

                db.session.commit()
            else:
                
                admins = User.query.filter_by(role='admin').all()
                for admin_user in admins:
                    notif = Notification(
                        user_id=admin_user.id,
                        message=f'🚨 URGENT! Breakdown on {ride.origin} → {ride.destination} and NO replacement vehicle available!'
                    )
                    db.session.add(notif)
                db.session.commit()

    flash(f'Ride status updated to {new_status}.', 'success')
    return redirect(f'/rides/{ride_id}')


@rides.route('/disputes/submit', methods=['POST'])
@login_required
def submit_dispute():
    from scholar_ride.models import Dispute
    reported_user_id = request.form.get('reported_user_id')
    ride_id = request.form.get('ride_id')
    description = request.form.get('description')

    existing_count = Dispute.query.filter_by(
        reported_by=current_user.id,
        ride_id=ride_id
    ).count()

    if existing_count >= 2:
        flash('You have reached the maximum of 2 reports for this ride.', 'warning')
        return redirect(f'/rides/{ride_id}')

    dispute = Dispute(
        reported_by=current_user.id,
        reported_user=reported_user_id,
        ride_id=ride_id,
        description=description
    )
    db.session.add(dispute)
    db.session.commit()
    flash('Dispute submitted. Admin will review it shortly.', 'success')
    return redirect(f'/rides/{ride_id}')

@rides.route('/rides/<int:ride_id>/review', methods=['GET', 'POST'])
@login_required
def leave_review(ride_id):
    from scholar_ride.models import Review
    ride = Ride.query.get_or_404(ride_id)

    booking = Booking.query.filter_by(
        ride_id=ride_id,
        student_id=current_user.id,
        status='confirmed'
    ).first()

    if not booking:
        flash('You can only review rides you were confirmed on.', 'danger')
        return redirect('/bookings/my')

    if ride.status != 'completed':
        flash('You can only review a ride after it has been completed.', 'warning')
        return redirect('/bookings/my')

    if not ride.completed_at or ride.completed_at < datetime.now() - timedelta(minutes=30):
        flash('The 30 minute review window for this ride has closed.', 'warning')
        return redirect('/bookings/my')

    existing = Review.query.filter_by(
        ride_id=ride_id,
        reviewer_id=current_user.id
    ).first()
    if existing:
        flash('You have already reviewed this ride.', 'warning')
        return redirect('/bookings/my')

    driver = User.query.get(ride.driver_id)

    if request.method == 'POST':
        rating = int(request.form.get('rating'))
        comment = request.form.get('comment')

        review = Review(
            ride_id=ride_id,
            reviewer_id=current_user.id,
            driver_id=ride.driver_id,
            rating=rating,
            comment=comment
        )
        db.session.add(review)

        notif = Notification(
            user_id=ride.driver_id,
            message=f'{current_user.full_name} left you a {rating}⭐ review.'
        )
        db.session.add(notif)
        db.session.commit()

        flash('Review submitted! Thank you.', 'success')
        return redirect('/bookings/my')

    return render_template('rides/review.html', ride=ride, driver=driver)


@rides.route('/driver/<int:driver_id>/reviews')
@login_required
def driver_reviews(driver_id):
    from scholar_ride.models import Review
    driver = User.query.get_or_404(driver_id)
    reviews = Review.query.filter_by(driver_id=driver_id).order_by(Review.created_at.desc()).all()
    avg_rating = round(sum(r.rating for r in reviews) / len(reviews), 1) if reviews else 0
    return render_template('rides/driver_reviews.html', driver=driver, reviews=reviews, avg_rating=avg_rating)


@rides.route('/rides/<int:ride_id>/broadcast', methods=['POST'])
@login_required
def broadcast_message(ride_id):
    ride = Ride.query.get_or_404(ride_id)

    if current_user.id != ride.driver_id:
        flash('Not authorised.', 'danger')
        return redirect(f'/rides/{ride_id}')

    msg_type = request.form.get('msg_type')
    custom_msg = request.form.get('custom_msg', '').strip()

    if msg_type == 'delay':
        eta = request.form.get('eta', '').strip()
        message = f'⏰ Delay Update — Your ride from {ride.origin} to {ride.destination} is delayed. New ETA: {eta}.'
    elif msg_type == 'breakdown':
        message = f'🔧 Breakdown Alert — Your ride from {ride.origin} to {ride.destination} has broken down. Please check for updates.'
    elif msg_type == 'cancelled':
        message = f'❌ Ride Cancelled — Your ride from {ride.origin} to {ride.destination} has been cancelled by the driver.'
    elif msg_type == 'custom':
        if not custom_msg:
            flash('Please enter a message.', 'warning')
            return redirect(f'/rides/{ride_id}')
        message = f'📢 Driver Update — {custom_msg}'
    else:
        flash('Invalid message type.', 'danger')
        return redirect(f'/rides/{ride_id}')

    confirmed_bookings = Booking.query.filter_by(
        ride_id=ride_id, status='confirmed'
    ).all()

    for booking in confirmed_bookings:
        notif = Notification(user_id=booking.student_id, message=message)
        db.session.add(notif)

    db.session.commit()

    flash(f'Message sent to {len(confirmed_bookings)} passenger(s).', 'success')
    return redirect(f'/rides/{ride_id}')
@rides.route('/rides/<int:ride_id>/request-overflow', methods=['POST'])
@login_required
def request_overflow(ride_id):
    from scholar_ride.models import Vehicle, OverflowRequest
    ride = Ride.query.get_or_404(ride_id)

    
    if ride.available_seats > 0:
        flash('This ride still has seats available.', 'warning')
        return redirect(f'/rides/{ride_id}')

    
    existing = OverflowRequest.query.filter_by(
        original_ride_id=ride_id,
        status='pending'
    ).first()
    if existing:
        flash('A replacement bus has already been requested. Please wait.', 'info')
        return redirect(f'/rides/{ride_id}')

    
    vehicle = Vehicle.query.filter_by(
        status='available',
        vehicle_type=ride.vehicle_type
    ).filter(Vehicle.capacity >= ride.total_seats).first()

    if not vehicle:
        flash('No replacement vehicle available right now. Admin has been notified.', 'warning')
        
        admins = User.query.filter_by(role='admin').all()
        for admin_user in admins:
            notif = Notification(
                user_id=admin_user.id,
                message=f'⚠️ Student {current_user.full_name} requested overflow for ride {ride.origin} → {ride.destination} but NO vehicle is available!'
            )
            db.session.add(notif)
        db.session.commit()
        return redirect(f'/rides/{ride_id}')

    
    overflow = OverflowRequest(
        original_ride_id=ride_id,
        requesting_student_id=current_user.id,
        reason='full'
    )
    db.session.add(overflow)
    db.session.flush()

    
    drivers = User.query.filter_by(role='driver').all()
    for driver in drivers:
        notif = Notification(
            user_id=driver.id,
            message=f'🚌 OVERFLOW|{overflow.id}|Bus is full on {ride.origin} → {ride.destination}. Vehicle {vehicle.bus_number} ({vehicle.registration_number}) is available for you to take.'
        )
        db.session.add(notif)

    
    admins = User.query.filter_by(role='admin').all()
    for admin_user in admins:
        notif = Notification(
            user_id=admin_user.id,
            message=f'🚌 Overflow triggered for {ride.origin} → {ride.destination} by {current_user.full_name}. Vehicle {vehicle.bus_number} notified to drivers.'
        )
        db.session.add(notif)

    db.session.commit()
    flash('Replacement bus requested! A driver will be assigned shortly. You will be notified.', 'success')
    return redirect(f'/rides/{ride_id}')


@rides.route('/rides/overflow/<int:overflow_id>/accept', methods=['POST'])
@login_required
def accept_overflow(overflow_id):
    from scholar_ride.models import Vehicle, OverflowRequest
    overflow = OverflowRequest.query.get_or_404(overflow_id)

    if current_user.role != 'driver':
        flash('Only drivers can accept overflow requests.', 'danger')
        return redirect('/rides')

    if overflow.status != 'pending':
        flash('This overflow request has already been handled.', 'warning')
        return redirect('/rides/my')

    original_ride = overflow.original_ride

    
    vehicle = Vehicle.query.filter_by(
        status='available',
        vehicle_type=original_ride.vehicle_type
    ).filter(Vehicle.capacity >= original_ride.total_seats).first()

    if not vehicle:
        flash('No vehicle available anymore.', 'danger')
        return redirect('/rides/my')

    
    new_ride = Ride(
        driver_id=current_user.id,
        origin=original_ride.origin,
        destination=original_ride.destination,
        departure_time=original_ride.departure_time,
        available_seats=vehicle.capacity,
        total_seats=vehicle.capacity,
        vehicle_type=vehicle.vehicle_type,
        vehicle_model=vehicle.make_model,
        registration_number=vehicle.registration_number
    )
    db.session.add(new_ride)
    db.session.flush()

    
    vehicle.status = 'on_trip'
    vehicle.current_driver_id = current_user.id
    vehicle.current_ride_id = new_ride.id


    overflow.status = 'accepted'
    overflow.new_ride_id = new_ride.id

    
    if overflow.reason == 'breakdown':
        bookings = Booking.query.filter_by(
            ride_id=original_ride.id,
            status='confirmed'
        ).all()
        for booking in bookings:
            new_booking = Booking(
                ride_id=new_ride.id,
                student_id=booking.student_id,
                status='confirmed'
            )
            db.session.add(new_booking)
            booking.status = 'cancelled'
            new_ride.available_seats -= 1

            notif = Notification(
                user_id=booking.student_id,
                message=f'✅ Your booking has been transferred to a replacement bus ({vehicle.bus_number}) for {original_ride.origin} → {original_ride.destination}. Driver: {current_user.full_name}'
            )
            db.session.add(notif)

    
    elif overflow.reason == 'full' and overflow.requesting_student_id:
        new_booking = Booking(
            ride_id=new_ride.id,
            student_id=overflow.requesting_student_id,
            status='confirmed'
        )
        db.session.add(new_booking)
        new_ride.available_seats -= 1

        notif = Notification(
            user_id=overflow.requesting_student_id,
            message=f'✅ A replacement bus ({vehicle.bus_number}) has been assigned for you! {original_ride.origin} → {original_ride.destination}. Driver: {current_user.full_name}'
        )
        db.session.add(notif)

    
    notif = Notification(
        user_id=current_user.id,
        message=f'✅ You have been assigned {vehicle.bus_number} ({vehicle.registration_number}) for {original_ride.origin} → {original_ride.destination} at {original_ride.departure_time.strftime("%H:%M")}'
    )
    db.session.add(notif)

  
    other_drivers = User.query.filter(
        User.role == 'driver',
        User.id != current_user.id
    ).all()
    for driver in other_drivers:
        notif = Notification(
            user_id=driver.id,
            message=f'ℹ️ Overflow trip for {original_ride.origin} → {original_ride.destination} has been accepted by {current_user.full_name}.'
        )
        db.session.add(notif)

    
    admins = User.query.filter_by(role='admin').all()
    for admin_user in admins:
        notif = Notification(
            user_id=admin_user.id,
            message=f'✅ Driver {current_user.full_name} accepted overflow for {original_ride.origin} → {original_ride.destination}. Vehicle: {vehicle.bus_number}'
        )
        db.session.add(notif)

    db.session.commit()
    flash(f'You have accepted the trip! Vehicle {vehicle.bus_number} is now assigned to you.', 'success')
    return redirect(f'/rides/{new_ride.id}')
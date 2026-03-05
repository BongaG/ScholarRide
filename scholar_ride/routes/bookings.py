from flask import Blueprint, redirect, flash, render_template
from flask_login import login_required, current_user
from scholar_ride import db
from scholar_ride.models import Booking, Ride, Notification

bookings = Blueprint('bookings', __name__)


@bookings.route('/bookings/request/<int:ride_id>', methods=['POST'])
@login_required
def request_seat(ride_id):
    ride = Ride.query.get_or_404(ride_id)

    if ride.available_seats <= 0:
        flash('Sorry, this ride is full.', 'danger')
        return redirect(f'/rides/{ride_id}')

    # Check double booking on same ride
    existing = Booking.query.filter_by(
        ride_id=ride_id, student_id=current_user.id
    ).first()
    if existing:
        flash('You have already requested this ride.', 'warning')
        return redirect(f'/rides/{ride_id}')

    # Check if user already has an active booking on any ride
    active_booking = Booking.query.join(Ride).filter(
        Booking.student_id == current_user.id,
        Booking.status.in_(['pending', 'confirmed']),
        Ride.status.in_(['active', 'delayed'])
    ).first()

    if active_booking:
        active_ride = Ride.query.get(active_booking.ride_id)
        flash(
            f'You already have an active booking for the ride from '
            f'{active_ride.origin} to {active_ride.destination}. '
            f'You can only book one ride at a time.',
            'danger'
        )
        return redirect(f'/rides/{ride_id}')

    booking = Booking(ride_id=ride_id, student_id=current_user.id)
    db.session.add(booking)

    msg = f'{current_user.full_name} has requested a seat on your ride to {ride.destination}.'
    notif = Notification(user_id=ride.driver_id, message=msg)
    db.session.add(notif)

    db.session.commit()
    flash('Seat requested! Waiting for driver approval.', 'success')
    return redirect(f'/rides/{ride_id}')


@bookings.route('/bookings/<int:booking_id>/approve')
@login_required
def approve_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    ride = Ride.query.get(booking.ride_id)

    if current_user.id != ride.driver_id:
        flash('Not authorised.', 'danger')
        return redirect('/rides')

    if ride.available_seats <= 0:
        flash('No seats available.', 'danger')
        return redirect(f'/rides/{ride.id}')

    booking.status = 'confirmed'
    ride.available_seats -= 1

    msg = f'Your seat on the ride from {ride.origin} to {ride.destination} has been CONFIRMED!'
    notif = Notification(user_id=booking.student_id, message=msg)
    db.session.add(notif)
    db.session.commit()

    flash('Booking approved.', 'success')
    return redirect(f'/rides/{ride.id}')


@bookings.route('/bookings/<int:booking_id>/reject')
@login_required
def reject_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    ride = Ride.query.get(booking.ride_id)

    if current_user.id != ride.driver_id:
        flash('Not authorised.', 'danger')
        return redirect('/rides')

    booking.status = 'cancelled'

    msg = f'Unfortunately your seat request for the ride to {ride.destination} was not approved.'
    notif = Notification(user_id=booking.student_id, message=msg)
    db.session.add(notif)
    db.session.commit()

    flash('Booking rejected.', 'info')
    return redirect(f'/rides/{ride.id}')


@bookings.route('/bookings/<int:booking_id>/cancel')
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    ride = Ride.query.get(booking.ride_id)

    if current_user.id != booking.student_id:
        flash('Not authorised.', 'danger')
        return redirect('/rides')

    if booking.status == 'confirmed':
        ride.available_seats += 1

    booking.status = 'cancelled'

    msg = f'{current_user.full_name} has cancelled their booking for your ride to {ride.destination}.'
    notif = Notification(user_id=ride.driver_id, message=msg)
    db.session.add(notif)
    db.session.commit()

    flash('Your booking has been cancelled.', 'info')
    return redirect('/bookings/my')


@bookings.route('/bookings/my')
@login_required
def my_bookings():
    all_bookings = Booking.query.filter_by(
        student_id=current_user.id
    ).order_by(Booking.booking_date.desc()).all()
    return render_template('bookings/my_bookings.html', bookings=all_bookings)
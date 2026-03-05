from flask import Blueprint, render_template, request, redirect, flash
from flask_login import login_required, current_user
from scholar_ride import db
from scholar_ride.models import Ride, Booking
from datetime import datetime
from scholar_ride.models import Ride, Booking, Notification, User

rides = Blueprint('rides', __name__)


@rides.route('/')
@rides.route('/rides')
@login_required
def index():
    origin = request.args.get('origin', '')
    destination = request.args.get('destination', '')
    date = request.args.get('date', '')

    query = Ride.query.filter(Ride.status != 'cancelled')

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
    if current_user.role not in ['driver', 'staff']:
        flash('Only drivers and staff can post rides.', 'danger')
        return redirect('/rides')

    if request.method == 'POST':
        origin = request.form.get('origin')
        destination = request.form.get('destination')
        departure_date = request.form.get('departure_date')
        departure_time = request.form.get('departure_time')
        seats = int(request.form.get('seats'))

        departure_dt = datetime.strptime(
            f'{departure_date} {departure_time}', '%Y-%m-%d %H:%M'
        )

        ride = Ride(
            driver_id=current_user.id,
            origin=origin,
            destination=destination,
            departure_time=departure_dt,
            available_seats=seats,
            total_seats=seats
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

    return render_template('rides/detail.html',
                           ride=ride,
                           bookings=bookings,
                           already_booked=already_booked,
                           booking_status=booking_status)


@rides.route('/rides/<int:ride_id>/update', methods=['POST'])
@login_required
def update_ride(ride_id):
    ride = Ride.query.get_or_404(ride_id)

    if current_user.id != ride.driver_id:
        flash('Not authorised.', 'danger')
        return redirect(f'/rides/{ride_id}')

    new_status = request.form.get('status')
    ride.status = new_status
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

    flash(f'Ride status updated to {new_status}.', 'success')
    return redirect(f'/rides/{ride_id}')


@rides.route('/disputes/submit', methods=['POST'])
@login_required
def submit_dispute():
    from scholar_ride.models import Dispute
    reported_user_id = request.form.get('reported_user_id')
    ride_id = request.form.get('ride_id')
    description = request.form.get('description')

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
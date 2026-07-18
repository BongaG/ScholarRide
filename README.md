Scholar Ride

A ride booking app for DUT students staff and drivers built with Flask

What it does

DUT students often need transport between campuses or residences and there is no proper system for it usually people just use WhatsApp groups Scholar Ride lets students and staff post or book rides drivers manage a shared vehicle fleet admins approve accounts and handle disputes

Main features

Separate flows for students staff drivers and admins
Registration is tied to a DUT email dut4life ac za or dut ac za and checked against the student number new accounts need OTP email verification and admin approval before they can log in
Students request seats on a ride and drivers approve or reject them
If a ride fills up or a vehicle breaks down mid route the app looks for another vehicle notifies drivers and moves the affected bookings over automatically
Reviews after a ride and a dispute system if something goes wrong
Admin dashboard for approvals fleet status analytics and support inquiries
Ride maps using Leaflet and MapTiler

Stack

Python Flask with blueprints SQLAlchemy SQLite Flask Login Flask Bcrypt Flask Mail Jinja2 Gunicorn for deployment

Structure

scholar_ride folder contains init file for the app factory config file models file with User Ride Booking Vehicle Dispute Review and more a routes folder with auth rides bookings admin and notifications and a templates folder

The hardest part

Handling a ride that breaks down or fills up mid route it has to find a replacement vehicle notify available drivers let one accept the trip move the affected students bookings to the new ride and notify them with the new drivers details I built this as a small state machine across the Ride Vehicle and OverflowRequest models instead of one big conditional so it is easier to extend later

Running it locally

git clone https://github.com/BongaG/ScholarRide.git
cd ScholarRide
python -m venv venv then activate it
pip install -r requirements.txt

You will need a env file with SECRET_KEY MAIL settings and MAPTILER_KEY

python run.py

Not done yet

Live GPS tracking on the map
Recurring rides for regular commuters
Waitlists for full rides
SMS or WhatsApp notifications

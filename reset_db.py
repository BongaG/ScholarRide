from scholar_ride import create_app, db

app = create_app()
with app.app_context():
    db.create_all()
    print('Done - all tables updated')
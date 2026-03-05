from scholar_ride import create_app, db

app = create_app()
with app.app_context():
    try:
        with db.engine.connect() as conn:
            conn.execute(db.text("ALTER TABLE user ADD COLUMN approval_status VARCHAR(20) DEFAULT 'pending'"))
            conn.commit()
        print('Column added successfully')
    except Exception as e:
        print(f'Error: {e}')
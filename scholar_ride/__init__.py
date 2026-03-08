from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from .config import Config

db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
mail = Mail()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    @app.context_processor
    def inject_unread_count():
        from flask_login import current_user
        from .models import Notification
        if current_user.is_authenticated:
            unread = Notification.query.filter_by(
                user_id=current_user.id, is_read=False
            ).count()
            return dict(unread_count=unread)
        return dict(unread_count=0)
    
    @app.context_processor
    def inject_maptiler():
        return dict(maptiler_key=app.config.get('MAPTILER_KEY'))

    from .routes.auth import auth
    from .routes.rides import rides
    from .routes.bookings import bookings
    from .routes.admin import admin
    from .routes.notifications import notifications

    app.register_blueprint(auth)
    app.register_blueprint(rides)
    app.register_blueprint(bookings)
    app.register_blueprint(admin)
    app.register_blueprint(notifications)

    return app
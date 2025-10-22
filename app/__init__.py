from flask import Flask, request, session
from flask_admin import Admin
from flask_babel import Babel
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from sqlalchemy import text


def get_locale():
    if request.args.get('lang'):
        session['lang'] = request.args.get('lang')
    return session.get('lang', 'en')

app = Flask(__name__)
csrf = CSRFProtect(app)
babel = Babel(app, locale_selector=get_locale)
admin = Admin(app, template_mode='bootstrap4')
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = 'login'

@app.before_request
def enable_foreign_keys():
    if db.engine.url.get_backend_name() == 'sqlite':
        db.session.execute(text("PRAGMA foreign_keys=ON"))

from app import views, models
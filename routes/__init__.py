from flask import Blueprint

# Create blueprints
main_bp = Blueprint('main', __name__)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
payment_bp = Blueprint('payment', __name__, url_prefix='/payment')

from . import main
from . import admin
from . import payment

def register_blueprints(app):
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(payment_bp)
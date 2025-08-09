from flask import Flask
from app.config import Config

from app.routes.home import home_bp
#from app.database import initialize_db

def create_app():
    app = Flask(__name__)

    # Load configuration from Config class
    app.config.from_object(Config)

    # Initialiser la base de données
    #initialize_db()

    #Blueprints
    app.register_blueprint(home_bp)

    return app
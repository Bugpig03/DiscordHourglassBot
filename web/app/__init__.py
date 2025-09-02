from flask import Blueprint, render_template
from flask import Flask
from app.config import Config
from app.routes.home import home_bp
from app.routes.top import top_bp
from app.routes.users import users_bp
from app.routes.servers import servers_bp
from app.routes.user_profile import user_profile_bp
from app.routes.server_profile import server_profile_bp
from app.routes.graphs import graphs_bp
from app.routes.api import api_bp

def create_app():
    app = Flask(__name__)

    # Load configuration from Config class
    app.config.from_object(Config)

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html"), 404

    #Blueprints
    app.register_blueprint(home_bp)
    app.register_blueprint(top_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(servers_bp)
    app.register_blueprint(user_profile_bp)
    app.register_blueprint(server_profile_bp)
    app.register_blueprint(graphs_bp)
    app.register_blueprint(api_bp)

    return app
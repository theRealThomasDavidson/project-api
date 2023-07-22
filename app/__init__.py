from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import environ
from urllib.parse import quote
from flask_migrate import Migrate
from flask_cors import CORS
from dotenv import dotenv_values, load_dotenv
from logging import warning


app = None
db = SQLAlchemy()  # Create an instance of SQLAlchemy
migrate = Migrate()
dotenv_path = '.env'
load_dotenv()
def create_app():
    substitution_dict = dict(dotenv_values(dotenv_path))
    from app.models.tag import Tag
    from app.models.project import Project
    from app.models.description import Description
    app = Flask(__name__)
    CORS(app, supports_credentials=True, resources={
            r"/*": {"origins": substitution_dict.get("CORS_ORIGINS").split(",")}
        })
    # Configuration and other app setup
    app.config['SQLALCHEMY_DATABASE_URI'] = generate_database_uri()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize the db object with your Flask application
    db.init_app(app)
    migrate.init_app(app, db)
    from app.controller.controller import controller_bp

    app.register_blueprint(controller_bp, url_prefix='/projects')

    return app


def generate_database_uri():
    db_username = environ.get('DB_USERNAME')
    db_password = environ.get('DB_PASSWORD')
    db_host = environ.get('DB_HOST')
    db_name = environ.get('DB_NAME')
    db_port = "3306"


    # Encode the username and password as bytes
    encoded_username = quote(db_username.encode('utf-8'), safe='')
    encoded_password = quote(db_password.encode('utf-8'), safe='')
    # Construct the database URI with encoded username and password
    return f'mysql+pymysql://{encoded_username}:{encoded_password}@{db_host}:{db_port}/{db_name}'

app = create_app()

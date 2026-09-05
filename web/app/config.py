"""Application configuration module."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()


class Config:
    """Flask application configuration settings loaded from environment variables."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev_secret_key")
    DB_NAME = os.environ.get("POSTGRESQL_DBNAME", "devhourglass")
    DB_USER = os.environ.get("POSTGRESQL_USER", "postgres")
    DB_PASSWORD = os.environ.get("POSTGRESQL_PASSWORD", "admin")
    DB_HOST = os.environ.get("POSTGRESQL_HOST", "localhost")
    DB_PORT = int(os.environ.get("POSTGRESQL_PORT", "5432"))
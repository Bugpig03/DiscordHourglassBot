# Variable environment configurationS
from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    DB_NAME = os.getenv("POSTGRESQL_DBNAME")
    DB_USER = os.getenv("POSTGRESQL_USER")
    DB_PASSWORD = os.getenv("POSTGRESQL_PASSWORD")
    DB_HOST = os.getenv("POSTGRESQL_HOST")
    DB_PORT = int(os.getenv("POSTGRESQL_PORT"))
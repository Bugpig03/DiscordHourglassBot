# Variable environment configurationS
import os

debug = False

if debug == True:
    from dotenv import load_dotenv
    load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    DB_NAME = os.environ.get("POSTGRESQL_DBNAME")
    DB_USER = os.environ.get("POSTGRESQL_USER")
    DB_PASSWORD = os.environ.get("POSTGRESQL_PASSWORD")
    DB_HOST = os.environ.get("POSTGRESQL_HOST")
    DB_PORT = int(os.environ.get("POSTGRESQL_PORT"))
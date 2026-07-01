import os

from dotenv import load_dotenv

from db.connection import get_database_url

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "Polly's Pop — Production & Inventory")
DEBUG = os.getenv("DEBUG", "false").lower() in {"1", "true", "yes"}
DATABASE_URL = get_database_url()

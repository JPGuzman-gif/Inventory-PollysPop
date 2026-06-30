import os

from dotenv import load_dotenv

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "Polly's Pop — Production & Inventory")
DEBUG = os.getenv("DEBUG", "false").lower() in {"1", "true", "yes"}
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/pollyspop.db")

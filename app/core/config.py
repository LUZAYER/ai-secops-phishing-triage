import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DATABASE_PATH = os.getenv("DATABASE_PATH", "state/alerts.db")
    TEMPLATE_DIR  = os.getenv("TEMPLATE_DIR",  "app/templates")
    REPORTS_DIR   = os.getenv("REPORTS_DIR",   "reports")
    DATA_FILE     = os.getenv("DATA_FILE",     "data/reports.json")
    HOST          = os.getenv("HOST", "0.0.0.0")
    PORT          = int(os.getenv("PORT", 8000))

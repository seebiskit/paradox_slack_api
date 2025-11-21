import os
from dotenv import load_dotenv
load_dotenv()
from google_sheets_sync import sheets_sync

sheets_sync.test_connection()
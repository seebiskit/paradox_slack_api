import os
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from typing import List, Dict, Optional

# Configuration
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
WORKSHEET_NAME = os.getenv("WORKSHEET_NAME", "Metrics")
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")

# Required scopes for Google Sheets API
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

class GoogleSheetsSync:
    def __init__(self):
        self.sheet_id = GOOGLE_SHEET_ID
        self.worksheet_name = WORKSHEET_NAME
        self.credentials_file = CREDENTIALS_FILE
        self._client = None
        self._sheet = None
        self._worksheet = None

    def _get_client(self):
        """Get or create authenticated gspread client"""
        if self._client is None:
            try:
                creds = Credentials.from_service_account_file(
                    self.credentials_file,
                    scopes=SCOPES
                )
                self._client = gspread.authorize(creds)
            except FileNotFoundError:
                print(f"Warning: Credentials file '{self.credentials_file}' not found.")
                return None
            except Exception as e:
                print(f"Error initializing Google Sheets client: {e}")
                return None
        return self._client

    def _get_worksheet(self):
        """Get or create worksheet reference"""
        if self._worksheet is None:
            client = self._get_client()
            if not client or not self.sheet_id:
                return None
            try:
                self._sheet = client.open_by_key(self.sheet_id)
                self._worksheet = self._sheet.worksheet(self.worksheet_name)
            except gspread.WorksheetNotFound:
                # Create the worksheet if it doesn't exist
                self._worksheet = self._sheet.add_worksheet(
                    title=self.worksheet_name,
                    rows=1000,
                    cols=10
                )
            except Exception as e:
                print(f"Error accessing worksheet: {e}")
                return None
        return self._worksheet

    def is_configured(self) -> bool:
        """Check if Google Sheets integration is properly configured"""
        return bool(self.sheet_id and os.path.exists(self.credentials_file))

    def ensure_headers_exist(self) -> bool:
        """Ensure the sheet has the correct headers, create if needed"""
        if not self.is_configured():
            return False

        try:
            worksheet = self._get_worksheet()
            if not worksheet:
                return False

            expected_headers = ["Date", "Category", "Metric", "Value", "Units", "User", "Notes"]

            # Check current headers
            try:
                current_headers = worksheet.row_values(1)
            except:
                current_headers = []

            if current_headers != expected_headers:
                # Update headers
                worksheet.update('A1:G1', [expected_headers])
                print("Headers updated successfully")

            return True

        except Exception as e:
            print(f"Error ensuring headers exist: {e}")
            return False

    def sync_metrics(self, category_name: str, metric_entries: List[Dict],
                    metric_date: str, user_display_name: str, notes: Optional[str] = None) -> bool:
        """
        Sync metrics to Google Sheets in real-time

        Args:
            category_name: Name of the category (e.g., "11 AM Sermon Attendance")
            metric_entries: List of dicts with 'metric_name', 'value', 'units'
            metric_date: Date in YYYY-MM-DD format
            user_display_name: Display name of user who logged the metric
            notes: Optional notes

        Returns:
            bool: True if sync was successful, False otherwise
        """
        if not self.is_configured():
            print("Google Sheets sync not configured, skipping...")
            return False

        try:
            # Ensure headers exist before adding data
            if not self.ensure_headers_exist():
                return False

            worksheet = self._get_worksheet()
            if not worksheet:
                return False

            # Prepare rows to add (one per metric)
            rows_to_add = []
            for entry in metric_entries:
                row = [
                    metric_date,                    # Date
                    category_name,                  # Category
                    entry['metric_name'],           # Metric
                    entry['value'],                 # Value
                    entry.get('units', ''),         # Units
                    user_display_name,              # User
                    notes or ''                     # Notes
                ]
                rows_to_add.append(row)

            # Append rows to sheet
            worksheet.append_rows(rows_to_add, value_input_option='RAW')
            print(f"Successfully synced {len(rows_to_add)} metrics to Google Sheets")
            return True

        except Exception as e:
            print(f"Error syncing metrics to Google Sheets: {e}")
            return False

    def test_connection(self) -> bool:
        """Test the Google Sheets connection"""
        if not self.is_configured():
            print("Google Sheets not configured - missing credentials.json or GOOGLE_SHEET_ID")
            return False

        try:
            client = self._get_client()
            if not client:
                print("Failed to create Google Sheets client")
                return False

            # Try to open the sheet
            sheet = client.open_by_key(self.sheet_id)
            sheet_title = sheet.title
            print(f"Google Sheets connection successful! Sheet: {sheet_title}")

            # Also verify worksheet access
            worksheet = self._get_worksheet()
            if worksheet:
                print(f"Worksheet '{self.worksheet_name}' accessible")

            return True

        except gspread.SpreadsheetNotFound:
            print(f"Spreadsheet not found. Make sure the sheet ID is correct and the service account has access.")
            print(f"Share your spreadsheet with: {self._get_service_account_email()}")
            return False
        except Exception as e:
            print(f"Error testing Google Sheets connection: {e}")
            return False

    def _get_service_account_email(self) -> str:
        """Get the service account email for sharing instructions"""
        try:
            import json
            with open(self.credentials_file) as f:
                creds = json.load(f)
                return creds.get('client_email', 'unknown')
        except:
            return 'unknown'

# Global instance
sheets_sync = GoogleSheetsSync()

def sync_metrics_to_sheets(category_name: str, metric_entries: List[Dict],
                          metric_date: str, user_display_name: str, notes: Optional[str] = None) -> bool:
    """
    Convenience function to sync metrics to Google Sheets

    Usage:
        sync_metrics_to_sheets(
            category_name="11 AM Sermon Attendance",
            metric_entries=[
                {"metric_name": "Adults", "value": 100, "units": "people"},
                {"metric_name": "Children", "value": 50, "units": "people"}
            ],
            metric_date="2025-11-21",
            user_display_name="Sawyer Martin",
            notes="Great turnout!"
        )
    """
    return sheets_sync.sync_metrics(category_name, metric_entries, metric_date, user_display_name, notes)

if __name__ == "__main__":
    # Test the connection when run directly
    from dotenv import load_dotenv
    load_dotenv()

    # Reinitialize with loaded env vars
    sheets_sync.sheet_id = os.getenv("GOOGLE_SHEET_ID")
    sheets_sync.worksheet_name = os.getenv("WORKSHEET_NAME", "Metrics")

    sheets_sync.test_connection()

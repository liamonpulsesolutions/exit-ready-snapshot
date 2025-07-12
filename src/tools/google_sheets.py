import os
import gspread
from google.oauth2.service_account import Credentials
from typing import Dict, Any, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class GoogleSheetsLogger:
    """Handle logging to Google Sheets CRM and Responses"""
    
    def __init__(self):
        self.creds_path = os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH')
        self.crm_sheet_id = os.getenv('CRM_SPREADSHEET_ID')
        self.responses_sheet_id = os.getenv('RESPONSES_SPREADSHEET_ID')
        self.client = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Sheets"""
        try:
            if not self.creds_path or not os.path.exists(self.creds_path):
                logger.warning("Google Sheets credentials not found. Using mock mode.")
                return
            
            scope = ['https://spreadsheets.google.com/feeds',
                     'https://www.googleapis.com/auth/drive']
            
            creds = Credentials.from_service_account_file(self.creds_path, scopes=scope)
            self.client = gspread.authorize(creds)
            logger.info("Successfully authenticated with Google Sheets")
            
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Sheets: {e}")
            self.client = None
    
    def log_to_crm(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Log user data to CRM sheet"""
        try:
            if not self.client:
                logger.info("Mock mode: Would log to CRM:")
                logger.info(f"  UUID: {user_data.get('uuid')}")
                logger.info(f"  Name: {user_data.get('name')}")
                logger.info(f"  Email: {user_data.get('email')}")
                return {"status": "success", "mode": "mock"}
            
            # Open CRM sheet
            sheet = self.client.open_by_key(self.crm_sheet_id).sheet1
            
            # Prepare row data
            row = [
                user_data.get('uuid'),
                datetime.now().isoformat(),
                user_data.get('name'),
                user_data.get('email'),
                user_data.get('industry'),
                user_data.get('years_in_business'),
                user_data.get('age_range'),
                user_data.get('exit_timeline'),
                user_data.get('location')
            ]
            
            # Append to sheet
            sheet.append_row(row)
            
            return {"status": "success", "mode": "live"}
            
        except Exception as e:
            logger.error(f"Failed to log to CRM: {e}")
            return {"status": "error", "error": str(e)}
    
    def log_responses(self, uuid: str, responses: Dict[str, Any]) -> Dict[str, Any]:
        """Log anonymized responses to responses sheet"""
        try:
            if not self.client:
                logger.info(f"Mock mode: Would log responses for UUID: {uuid}")
                return {"status": "success", "mode": "mock"}
            
            # Open responses sheet
            sheet = self.client.open_by_key(self.responses_sheet_id).sheet1
            
            # Prepare row data
            row = [uuid, datetime.now().isoformat()]
            
            # Add responses in order
            for i in range(1, 11):
                row.append(responses.get(f"q{i}", ""))
            
            # Append to sheet
            sheet.append_row(row)
            
            return {"status": "success", "mode": "live"}
            
        except Exception as e:
            logger.error(f"Failed to log responses: {e}")
            return {"status": "error", "error": str(e)}
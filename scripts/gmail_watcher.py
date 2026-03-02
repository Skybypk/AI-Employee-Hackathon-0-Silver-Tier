#!/usr/bin/env python3
"""
Gmail Watcher - Monitors Gmail for new emails using OAuth2 authentication
Part of the Personal AI Employee Silver Tier implementation
"""

import os
import sys
import json
import time
import logging
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any
import socket

# Try to import required packages, provide fallbacks
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GMAIL_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Gmail dependencies not installed: {e}")
    print("Install with: pip install google-auth google-auth-oauthlib google-api-python-client")
    GMAIL_AVAILABLE = False

# Configuration
VAULT_BASE = Path(__file__).parent / "AI_Employee_Vault"
INBOX_DIR = VAULT_BASE / "Inbox"
LOGS_DIR = VAULT_BASE / "Logs"
CREDENTIALS_FILE = Path(__file__).parent / "gmail_credentials.json"
TOKEN_FILE = Path(__file__).parent / "token.json"

# Scopes for Gmail API
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / "gmail_watcher.log" if LOGS_DIR.exists() else "gmail_watcher.log")
    ]
)
logger = logging.getLogger(__name__)


class GmailWatcher:
    """Monitors Gmail inbox for new messages and saves them to the vault."""
    
    def __init__(self, poll_interval: int = 60):
        self.poll_interval = poll_interval
        self.service: Optional[Any] = None
        self.last_message_id: Optional[str] = None
        self.running = False
        self.error_count = 0
        self.max_errors = 5
        self.retry_delay = 5  # seconds
        
    def authenticate(self) -> bool:
        """Authenticate with Gmail API using OAuth2."""
        if not GMAIL_AVAILABLE:
            logger.error("Gmail API dependencies not available")
            return False
            
        try:
            creds = None
            
            # Load existing token
            if TOKEN_FILE.exists():
                try:
                    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
                    logger.info("Loaded existing credentials")
                except Exception as e:
                    logger.warning(f"Failed to load token: {e}")
                    TOKEN_FILE.unlink(missing_ok=True)
                    creds = None
            
            # Refresh or get new credentials
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                        logger.info("Refreshed access token")
                    except Exception as e:
                        logger.warning(f"Token refresh failed: {e}")
                        creds = None
                
                if not creds:
                    if not CREDENTIALS_FILE.exists():
                        logger.error(
                            "Credentials file not found. Please download OAuth2 credentials "
                            "from Google Cloud Console and save as gmail_credentials.json"
                        )
                        return False
                    
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            CREDENTIALS_FILE, SCOPES
                        )
                        creds = flow.run_local_server(port=0)
                        logger.info("Authentication successful")
                    except Exception as e:
                        logger.error(f"Authentication failed: {e}")
                        return False
                
                # Save credentials
                try:
                    with open(TOKEN_FILE, "w") as token:
                        token.write(creds.to_json())
                    logger.info("Saved credentials token")
                except Exception as e:
                    logger.warning(f"Failed to save token: {e}")
            
            # Build service
            self.service = build("gmail", "v1", credentials=creds)
            logger.info("Gmail service initialized")
            return True
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    def get_latest_message_id(self) -> Optional[str]:
        """Get the ID of the most recent message in the inbox."""
        try:
            results = self.service.users().messages().list(
                userId="me",
                labelIds=["INBOX"],
                maxResults=1
            ).execute()
            
            messages = results.get("messages", [])
            if messages:
                return messages[0]["id"]
            return None
            
        except HttpError as e:
            logger.error(f"API error getting messages: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting latest message: {e}")
            raise
    
    def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a complete message by ID."""
        try:
            message = self.service.users().messages().get(
                userId="me",
                id=message_id,
                format="full"
            ).execute()
            
            # Extract relevant information
            headers = message.get("payload", {}).get("headers", [])
            email_data = {
                "id": message_id,
                "threadId": message.get("threadId"),
                "labelIds": message.get("labelIds", []),
                "snippet": message.get("snippet", ""),
                "internalDate": message.get("internalDate"),
                "subject": "",
                "from": "",
                "to": "",
                "date": "",
                "body": ""
            }
            
            for header in headers:
                name = header.get("name", "")
                value = header.get("value", "")
                if name.lower() == "subject":
                    email_data["subject"] = value
                elif name.lower() == "from":
                    email_data["from"] = value
                elif name.lower() == "to":
                    email_data["to"] = value
                elif name.lower() == "date":
                    email_data["date"] = value
            
            # Extract body
            body = self._extract_body(message)
            email_data["body"] = body
            
            return email_data
            
        except HttpError as e:
            logger.error(f"API error getting message {message_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting message {message_id}: {e}")
            return None
    
    def _extract_body(self, message: Dict[str, Any]) -> str:
        """Extract the text body from a message."""
        try:
            parts = message.get("payload", {}).get("parts", [])
            
            # Try to find text/plain part
            for part in parts:
                if part.get("mimeType") == "text/plain":
                    data = part.get("body", {}).get("data")
                    if data:
                        return base64.urlsafe_b64decode(data).decode("utf-8")
            
            # Fallback to body if no parts
            body = message.get("payload", {}).get("body", {})
            data = body.get("data")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8")
            
            return ""
            
        except Exception as e:
            logger.warning(f"Error extracting body: {e}")
            return ""
    
    def save_email_to_vault(self, email_data: Dict[str, Any]) -> Path:
        """Save an email to the inbox vault."""
        try:
            # Create filename from date and subject
            timestamp = datetime.fromtimestamp(int(email_data["internalDate"]) / 1000)
            safe_subject = "".join(
                c for c in email_data["subject"][:50]
                if c.isalnum() or c in " -_"
            ).strip()
            filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{safe_subject or 'No_Subject'}.json"
            
            filepath = INBOX_DIR / filename
            
            # Save email data
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(email_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved email to vault: {filename}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving email to vault: {e}")
            # Fallback: save to logs
            try:
                log_file = LOGS_DIR / f"email_save_error_{int(time.time())}.json"
                with open(log_file, "w") as f:
                    json.dump(email_data, f, indent=2)
                logger.warning(f"Saved email to logs due to error: {log_file}")
            except:
                pass
            raise
    
    def check_for_new_emails(self) -> int:
        """Check for and process new emails. Returns count of new emails."""
        try:
            current_message_id = self.get_latest_message_id()
            
            if not current_message_id:
                logger.debug("No messages in inbox")
                return 0
            
            # If this is the first check, just store the ID
            if self.last_message_id is None:
                self.last_message_id = current_message_id
                logger.info(f"Initial message ID: {current_message_id}")
                return 0
            
            # If no new messages
            if current_message_id == self.last_message_id:
                logger.debug("No new messages")
                return 0
            
            # Fetch and save all new messages
            new_count = 0
            results = self.service.users().messages().list(
                userId="me",
                labelIds=["INBOX"],
                maxResults=10
            ).execute()
            
            messages = results.get("messages", [])
            
            for msg in messages:
                msg_id = msg["id"]
                
                # Skip already processed messages
                if msg_id == self.last_message_id:
                    break
                
                email_data = self.get_message(msg_id)
                if email_data:
                    self.save_email_to_vault(email_data)
                    new_count += 1
            
            # Update last message ID
            self.last_message_id = current_message_id
            
            if new_count > 0:
                logger.info(f"Processed {new_count} new email(s)")
            
            return new_count
            
        except HttpError as e:
            if e.resp.status == 401:
                logger.error("Authentication error, attempting re-authentication")
                if self.authenticate():
                    return self.check_for_new_emails()
            logger.error(f"HTTP error checking emails: {e}")
            return 0
        except Exception as e:
            logger.error(f"Error checking for new emails: {e}")
            return 0
    
    def log_status(self, message: str):
        """Log status to the logs directory."""
        try:
            status_file = LOGS_DIR / "gmail_watcher_status.json"
            status = {
                "timestamp": datetime.now().isoformat(),
                "status": "running" if self.running else "stopped",
                "last_message_id": self.last_message_id,
                "error_count": self.error_count,
                "message": message
            }
            with open(status_file, "w") as f:
                json.dump(status, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write status: {e}")
    
    def run(self):
        """Main loop for watching Gmail."""
        logger.info("Starting Gmail Watcher...")
        self.running = True
        self.error_count = 0
        
        # Ensure directories exist
        INBOX_DIR.mkdir(parents=True, exist_ok=True)
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Authenticate
        if not self.authenticate():
            logger.error("Failed to authenticate. Running in demo mode...")
            # Run in demo mode - just log status
            while self.running:
                self.log_status("Demo mode - no Gmail credentials")
                time.sleep(self.poll_interval)
            return
        
        self.log_status("Authenticated and monitoring")
        
        # Main monitoring loop
        while self.running:
            try:
                new_emails = self.check_for_new_emails()
                self.error_count = 0  # Reset on success
                self.log_status(f"Monitoring - {new_emails} new emails")
                
            except socket.gaierror as e:
                logger.warning(f"Network error: {e}")
                self.error_count += 1
                self.log_status(f"Network error, retrying in {self.retry_delay}s")
                
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                self.error_count += 1
                self.log_status(f"Error: {str(e)}")
                
                # Auto-recovery: attempt re-authentication after max errors
                if self.error_count >= self.max_errors:
                    logger.warning("Max errors reached, attempting recovery...")
                    self.error_count = 0
                    if self.authenticate():
                        logger.info("Re-authentication successful")
                    else:
                        logger.error("Re-authentication failed, continuing in degraded mode")
            
            # Wait before next poll
            time.sleep(self.poll_interval)
    
    def stop(self):
        """Stop the watcher."""
        logger.info("Stopping Gmail Watcher...")
        self.running = False
        self.log_status("Stopped")


def main():
    """Entry point for Gmail Watcher."""
    import signal
    
    # Get poll interval from environment or use default
    poll_interval = int(os.environ.get("GMAIL_POLL_INTERVAL", "60"))
    
    watcher = GmailWatcher(poll_interval=poll_interval)
    
    # Handle shutdown signals
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        watcher.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start watching
    try:
        watcher.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        watcher.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

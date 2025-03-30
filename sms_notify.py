#!/usr/bin/env python3
"""
SMS Notification Utility for Database Status

This script sends SMS notifications about database issues or status changes.
It requires Twilio credentials to be set in environment variables.

Usage:
    python sms_notify.py "Your notification message here"
"""

import os
import sys
import argparse
from datetime import datetime

def send_sms_notification(message, to_number=None):
    """Send an SMS notification using Twilio"""
    # Check if Twilio credentials are set
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    from_number = os.environ.get('TWILIO_PHONE_NUMBER')
    
    if not account_sid or not auth_token or not from_number:
        print("Error: Twilio credentials not set in environment variables.")
        print("Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER.")
        return False
    
    # Use default recipient if none provided
    if not to_number:
        to_number = os.environ.get('NOTIFY_PHONE_NUMBER')
        
    if not to_number:
        print("Error: No recipient phone number provided.")
        print("Set NOTIFY_PHONE_NUMBER environment variable or provide --to argument.")
        return False
    
    try:
        # Import Twilio only when needed
        from twilio.rest import Client
        
        # Create Twilio client
        client = Client(account_sid, auth_token)
        
        # Add timestamp to message
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        full_message = f"[{timestamp}] {message}"
        
        # Send message
        sms = client.messages.create(
            body=full_message,
            from_=from_number,
            to=to_number
        )
        
        print(f"SMS notification sent: SID {sms.sid}")
        return True
    except ImportError:
        print("Error: Twilio package not installed.")
        print("Install it with: pip install twilio")
        return False
    except Exception as e:
        print(f"Error sending SMS notification: {str(e)}")
        return False

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Send SMS notifications about database status.')
    parser.add_argument('message', help='The message to send')
    parser.add_argument('--to', help='The phone number to send the notification to')
    
    args = parser.parse_args()
    
    # Send notification
    if send_sms_notification(args.message, args.to):
        print("Notification sent successfully.")
        sys.exit(0)
    else:
        print("Failed to send notification.")
        sys.exit(1)

if __name__ == '__main__':
    main()
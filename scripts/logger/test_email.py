#!/usr/bin/env python3
"""
Test script for email notification system.

This script tests the Amazon SES email configuration and sends a test email.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from email_notifier import EmailNotifier


def test_email_connection():
    """Test SMTP connection without sending email."""
    print("Testing Amazon SES SMTP connection...")
    
    try:
        notifier = EmailNotifier()
        
        if notifier.test_connection():
            print("✅ SMTP connection successful!")
            return True
        else:
            print("❌ SMTP connection failed!")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def send_test_email(recipient: str):
    """Send a test alert email."""
    print(f"\nSending test email to {recipient}...")
    
    try:
        notifier = EmailNotifier()
        
        success = notifier.send_alert(
            to_email=recipient,
            cryptocurrency="Bitcoin (TEST)",
            current_price=92450.50,
            target_price=90000.00,
            condition=">=",
            alert_name="Test Alert - System Check",
            timestamp=datetime.now()
        )
        
        if success:
            print("✅ Test email sent successfully!")
            print(f"   Check your inbox at {recipient}")
            return True
        else:
            print("❌ Failed to send test email!")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Main test function."""
    print("=" * 60)
    print("Crypto Price Logger - Email System Test")
    print("=" * 60)
    
    # Test connection
    connection_ok = test_email_connection()
    
    if not connection_ok:
        print("\n⚠️  Connection test failed. Check your .env file:")
        print("   - SES_SMTP_HOST")
        print("   - SES_SMTP_PORT")
        print("   - SES_SMTP_USER")
        print("   - SES_SMTP_PASS")
        sys.exit(1)
    
    # Ask if user wants to send test email
    print("\n" + "=" * 60)
    recipient = input("Enter email address to send test alert (or press Enter to skip): ").strip()
    
    if recipient:
        send_test_email(recipient)
    else:
        print("Skipping test email send.")
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()

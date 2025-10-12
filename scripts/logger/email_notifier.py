"""
Email Notifier using Amazon SES SMTP.

This module handles sending email alerts when cryptocurrency price
targets are reached.
"""

import os
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class EmailNotifier:
    """
    Email notification system using Amazon SES SMTP.
    
    Sends formatted email alerts when price conditions are met.
    """
    
    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_pass: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: int = 5
    ):
        """
        Initialize the email notifier.
        
        Args:
            smtp_host: SMTP server host (defaults to env var SES_SMTP_HOST)
            smtp_port: SMTP server port (defaults to env var SES_SMTP_PORT)
            smtp_user: SMTP username (defaults to env var SES_SMTP_USER)
            smtp_pass: SMTP password (defaults to env var SES_SMTP_PASS)
            from_email: Sender email address (defaults to env var EMAIL_FROM)
            from_name: Sender name (defaults to env var EMAIL_FROM_NAME)
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.smtp_host = smtp_host or os.getenv('SES_SMTP_HOST')
        self.smtp_port = int(smtp_port or os.getenv('SES_SMTP_PORT', '587'))
        self.smtp_user = smtp_user or os.getenv('SES_SMTP_USER')
        self.smtp_pass = smtp_pass or os.getenv('SES_SMTP_PASS')
        self.from_email = from_email or os.getenv('EMAIL_FROM')
        self.from_name = from_name or os.getenv('EMAIL_FROM_NAME', 'Crypto Logger')
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate that all required configuration is present."""
        required = {
            'SMTP Host': self.smtp_host,
            'SMTP Port': self.smtp_port,
            'SMTP User': self.smtp_user,
            'SMTP Password': self.smtp_pass,
            'From Email': self.from_email,
        }
        
        missing = [name for name, value in required.items() if not value]
        
        if missing:
            raise ValueError(
                f"Missing required email configuration: {', '.join(missing)}. "
                "Please check your .env file."
            )
    
    def _create_html_message(
        self,
        cryptocurrency: str,
        current_price: float,
        target_price: float,
        condition: str,
        alert_name: str,
        timestamp: Optional[datetime] = None
    ) -> str:
        """
        Create HTML email message.
        
        Args:
            cryptocurrency: Name of the cryptocurrency
            current_price: Current price that triggered the alert
            target_price: Target price from configuration
            condition: Condition that was met (>=, <=, ==)
            alert_name: Name of the alert
            timestamp: When the alert was triggered
            
        Returns:
            HTML formatted email body
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Determine emoji based on condition
        emoji = "🚀" if condition == ">=" else "📉" if condition == "<=" else "🎯"
        
        # Format prices
        price_format = "${:,.8f}" if current_price < 1 else "${:,.2f}"
        current_price_str = price_format.format(current_price)
        target_price_str = price_format.format(target_price)
        
        html = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f9f9f9;
                    border-radius: 10px;
                }}
                .header {{
                    background-color: #4CAF50;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background-color: white;
                    padding: 20px;
                    border-radius: 0 0 10px 10px;
                }}
                .alert-info {{
                    background-color: #e7f3ff;
                    border-left: 4px solid #2196F3;
                    padding: 15px;
                    margin: 20px 0;
                }}
                .price {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #4CAF50;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 20px;
                    font-size: 12px;
                    color: #666;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 15px 0;
                }}
                td {{
                    padding: 10px;
                    border-bottom: 1px solid #ddd;
                }}
                td:first-child {{
                    font-weight: bold;
                    width: 40%;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{emoji} Crypto Price Alert</h1>
                </div>
                <div class="content">
                    <h2>Alert: {alert_name}</h2>
                    <p>Your cryptocurrency price alert has been triggered!</p>
                    
                    <div class="alert-info">
                        <table>
                            <tr>
                                <td>Cryptocurrency:</td>
                                <td><strong>{cryptocurrency}</strong></td>
                            </tr>
                            <tr>
                                <td>Current Price:</td>
                                <td class="price">{current_price_str}</td>
                            </tr>
                            <tr>
                                <td>Target Price:</td>
                                <td>{target_price_str}</td>
                            </tr>
                            <tr>
                                <td>Condition:</td>
                                <td>{condition} ({"greater than or equal" if condition == ">=" else "less than or equal" if condition == "<=" else "equal"})</td>
                            </tr>
                            <tr>
                                <td>Triggered At:</td>
                                <td>{timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</td>
                            </tr>
                        </table>
                    </div>
                    
                    <p>This alert will be on cooldown for the configured period to prevent spam.</p>
                </div>
                <div class="footer">
                    <p>Sent by {self.from_name}</p>
                    <p>This is an automated message from your crypto price monitoring system.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _create_text_message(
        self,
        cryptocurrency: str,
        current_price: float,
        target_price: float,
        condition: str,
        alert_name: str,
        timestamp: Optional[datetime] = None
    ) -> str:
        """
        Create plain text email message.
        
        Args:
            cryptocurrency: Name of the cryptocurrency
            current_price: Current price that triggered the alert
            target_price: Target price from configuration
            condition: Condition that was met (>=, <=, ==)
            alert_name: Name of the alert
            timestamp: When the alert was triggered
            
        Returns:
            Plain text formatted email body
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Format prices
        price_format = "${:,.8f}" if current_price < 1 else "${:,.2f}"
        current_price_str = price_format.format(current_price)
        target_price_str = price_format.format(target_price)
        
        condition_text = {
            ">=": "greater than or equal",
            "<=": "less than or equal",
            "==": "equal"
        }.get(condition, condition)
        
        text = f"""
CRYPTO PRICE ALERT

Alert: {alert_name}

Your cryptocurrency price alert has been triggered!

Cryptocurrency: {cryptocurrency}
Current Price: {current_price_str}
Target Price: {target_price_str}
Condition: {condition} ({condition_text})
Triggered At: {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}

This alert will be on cooldown for the configured period to prevent spam.

---
Sent by {self.from_name}
This is an automated message from your crypto price monitoring system.
        """
        
        return text.strip()
    
    def send_alert(
        self,
        to_email: str,
        cryptocurrency: str,
        current_price: float,
        target_price: float,
        condition: str,
        alert_name: str,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Send a price alert email.
        
        Args:
            to_email: Recipient email address
            cryptocurrency: Name of the cryptocurrency
            current_price: Current price that triggered the alert
            target_price: Target price from configuration
            condition: Condition that was met (>=, <=, ==)
            alert_name: Name of the alert
            timestamp: When the alert was triggered
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Determine emoji for subject
        emoji = "🚀" if condition == ">=" else "📉" if condition == "<=" else "🎯"
        
        # Format price for subject
        price_format = "${:,.8f}" if current_price < 1 else "${:,.2f}"
        current_price_str = price_format.format(current_price)
        
        subject = f"{emoji} Crypto Alert: {cryptocurrency} reached {current_price_str}"
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{self.from_name} <{self.from_email}>"
        msg['To'] = to_email
        
        # Create both plain text and HTML versions
        text_body = self._create_text_message(
            cryptocurrency, current_price, target_price,
            condition, alert_name, timestamp
        )
        html_body = self._create_html_message(
            cryptocurrency, current_price, target_price,
            condition, alert_name, timestamp
        )
        
        # Attach both versions
        part1 = MIMEText(text_body, 'plain')
        part2 = MIMEText(html_body, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        # Send with retries
        for attempt in range(self.max_retries):
            try:
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)
                
                return True
                
            except smtplib.SMTPException as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    print(f"Failed to send email after {self.max_retries} attempts: {e}")
                    return False
            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    print(f"Unexpected error sending email: {e}")
                    return False
        
        return False
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str
    ) -> bool:
        """
        Send a custom email with HTML and text body.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML version of the email body
            text_body: Plain text version of the email body
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{self.from_name} <{self.from_email}>"
        msg['To'] = to_email
        
        # Attach both versions
        part1 = MIMEText(text_body, 'plain')
        part2 = MIMEText(html_body, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        # Send with retries
        for attempt in range(self.max_retries):
            try:
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)
                
                return True
                
            except smtplib.SMTPException as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    print(f"Failed to send email after {self.max_retries} attempts: {e}")
                    return False
            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    print(f"Unexpected error sending email: {e}")
                    return False
        
        return False
    
    def test_connection(self) -> bool:
        """
        Test the SMTP connection without sending an email.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
            return True
        except Exception as e:
            print(f"SMTP connection test failed: {e}")
            return False

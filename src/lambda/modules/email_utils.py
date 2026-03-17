# Email Module for AWS Automated Access Review
import boto3
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime

def send_report_email(narrative, csv_content, recipient_email):
    """
    Sends the security report via Amazon SES with a CSV attachment.
    """
    ses = boto3.client('ses')
    date_str = datetime.now().strftime('%Y-%m-%d')
    
    msg = MIMEMultipart('mixed')
    msg['Subject'] = f"AWS Access Review Report — {date_str}"
    msg['From'] = recipient_email # SES requires verified sender
    msg['To'] = recipient_email

    # HTML Body (The narrative)
    html_body = f"""
    <html>
    <head></head>
    <body>
      <h1>AWS Automated Access Review Summary</h1>
      <p style="white-space: pre-wrap;">{narrative}</p>
      <hr>
      <p>A detailed CSV report is attached to this email.</p>
    </body>
    </html>
    """
    msg_body = MIMEMultipart('alternative')
    msg_body.attach(MIMEText(html_body, 'html'))
    msg.attach(msg_body)

    # Attachment
    attachment = MIMEApplication(csv_content)
    attachment.add_header('Content-Disposition', 'attachment', filename=f"access-review-{date_str}.csv")
    msg.attach(attachment)

    try:
        response = ses.send_raw_email(
            Source=msg['From'],
            Destinations=[msg['To']],
            RawMessage={'Data': msg.as_string()}
        )
        return response['MessageId']
    except Exception as e:
        print(f"Error sending email via SES: {e}")
        return None

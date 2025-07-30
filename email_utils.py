
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
 
EMAIL_SENDER = "vumiiliakonga2@gmail.com"
EMAIL_PASSWORD = "uswi tjdv kzdg gjwz"


def send_verification_code(email, code):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your AI Invest Verification Code"
    msg["From"] = EMAIL_SENDER
    msg["To"] = email

    html = f"""
    <html>
    <body>
      <h2>Your Verification Code</h2>
      <p>Use the code below to verify your email:</p>
      <div style="font-size: 24px; font-weight: bold;">{code}</div>
      <p>This code will expire in 10 minutes.</p>
    </body>
    </html>
    """

    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, email, msg.as_string())
    except Exception as e:
        print("Email send error:", e)

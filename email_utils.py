
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
 
EMAIL_SENDER = "vumiiliakonga2@gmail.com"
EMAIL_PASSWORD = "uswi tjdv kzdg gjwz"

def send_verification_email(email, token):
    verify_link = f"https://ai-invest-app-ycr6.onrender.com/verify-email/{token}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Verify Your Email - AI Invest"
    msg["From"] = EMAIL_SENDER
    msg["To"] = email

    html = f"""
    <html>
    <body>
      <h2>Welcome to AI Invest!</h2>
      <p>Please click below to verify:</p>
      <a href="{verify_link}">Verify Email</a>
      <p>This link expires in 10 minutes.</p>
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

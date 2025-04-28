import smtplib
import os
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load environment variables
load_dotenv(".env")

# This is the test file for Email Notify functionality
QUIZMENTOR_EMAIL = os.getenv("QUIZMENTOR_EMAIL")
QUIZMENTOR_PASS = os.getenv("QUIZMENTOR_PASS")
# Debugging: Check if variables are loaded
print("Email:", QUIZMENTOR_EMAIL)
print("Password:", QUIZMENTOR_PASS)  # This should not be None!
def send_email(course, recipient_email):
    msg = MIMEMultipart()
    msg["From"] = QUIZMENTOR_EMAIL
    msg["To"] = recipient_email
    msg["Subject"] = f"Quiz Assigned: {course}"

    body = f"""Hello Student,

A new quiz for the course **{course}** has been assigned to you. Please check your dashboard to attempt the quiz.

Best regards,  
QuizMentor Team"""
    
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(QUIZMENTOR_EMAIL, QUIZMENTOR_PASS)
        server.sendmail(QUIZMENTOR_EMAIL, recipient_email, msg.as_string())
        server.quit()
        
        print(f"✅ Email sent to {recipient_email} for {course}")
    except Exception as e:
        print(f"❌ Error sending email: {e}")

if __name__ == "__main__":
    # Example usage
# any numbers of reciever add to this
    send_email("Operating Systems", "azharsharif042@gmail.com")

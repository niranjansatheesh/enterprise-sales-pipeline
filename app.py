# 1. Install dependencies: pip install twilio sendgrid
from twilio.rest import Client
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def trigger_otp_generation(target):
    otp = f"{random.randint(100000, 999999)}"
    st.session_state.auth_otp = otp
    st.session_state.auth_target = target
    st.session_state.auth_step = "verify"
    
    target_type = is_valid_input(target)
    
    if target_type == "phone":
        # --- TWILIO SMS INTEGRATION ---
        try:
            client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
            client.messages.create(
                body=f"Your MARKETPULSE verification code is: {otp}. It expires in 10 minutes.",
                from_=os.getenv("TWILIO_PHONE_NUMBER"),
                to=target.strip()
            )
        except Exception as e:
            st.error(f"Failed to send SMS: {e}")
            
    elif target_type == "email":
        # --- SENDGRID EMAIL INTEGRATION ---
        try:
            message = Mail(
                from_email=os.getenv("SENDGRID_FROM_EMAIL"),
                to_emails=target.strip(),
                subject="Your MARKETPULSE Verification Code",
                html_content=f"<h3>Verification Code</h3><p>Your security code is <strong>{otp}</strong>.</p>"
            )
            sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
            sg.send(message)
        except Exception as e:
            st.error(f"Failed to send Email: {e}")
import smtplib
from email.message import EmailMessage

def send_price_alert(event, price, secret_getter):
    host = secret_getter("SMTP_HOST")
    user = secret_getter("SMTP_USER")
    password = secret_getter("SMTP_PASSWORD")
    recipient = secret_getter("ALERT_TO")
    if not all([host, user, password, recipient]):
        return False
    port = int(secret_getter("SMTP_PORT", "587"))
    currency = event.get("currency", "USD")
    msg = EmailMessage()
    msg["Subject"] = f"TicketTracker price target reached: {event['event_name']}"
    msg["From"] = user
    msg["To"] = recipient
    msg.set_content(
        f"Your tracked ticket price target was reached.\\n\\n"
        f"Event: {event['event_name']}\\n"
        f"Marketplace: {event['platform']}\\n"
        f"Observed price: {price:.2f} {currency}\\n"
        f"Listing: {event['url']}\\n\\n"
        "This is a price observation you entered in TicketTracker."
    )
    try:
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
        return True
    except Exception:
        return False

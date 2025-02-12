import asyncio
import schedule
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import smtplib
from email.mime.text import MIMEText
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://user:password@localhost/dbname"
engine = create_engine(DATABASE_URL)


def send_email(to_email, seat_number, page_url):
    # Configure your email settings
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = "your-email@gmail.com"
    password = "your-app-specific-password"

    msg = MIMEText(
        f"""
    Good news! Seat {seat_number} is now available!
    
    Click here to book: {page_url}
    
    If you successfully book this seat, please click here to stop notifications:
    {your_confirmation_url}
    """
    )

    msg["Subject"] = f"Seat {seat_number} is Available!"
    msg["From"] = sender_email
    msg["To"] = to_email

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, password)
        server.send_message(msg)


def check_seats():
    # Get all notifications
    with engine.connect() as conn:
        results = conn.execute(text("SELECT * FROM notifications"))
        notifications = results.fetchall()

    driver = webdriver.Chrome()

    try:
        for notification in notifications:
            driver.get(notification.page_url)

            # Wait for seats to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "button"))
            )

            # Click zoom if needed
            zoom_button = driver.find_elements_by_css_selector(
                ".rounded-full.bg-gray-400.p-4"
            )
            if zoom_button:
                zoom_button[0].click()
                time.sleep(1)

            # Find the specific seat
            seat_buttons = driver.find_elements_by_xpath(
                f"//button[text()='{notification.seat_number}']"
            )

            if seat_buttons and not "cursor-not-allowed" in seat_buttons[
                0
            ].get_attribute("class"):
                # Seat is available!
                send_email(
                    notification.email, notification.seat_number, notification.page_url
                )

    finally:
        driver.quit()


def run_scheduler():
    schedule.every(10).minutes.do(check_seats)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    run_scheduler()

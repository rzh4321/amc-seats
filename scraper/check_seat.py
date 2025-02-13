import asyncio
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import smtplib
from email.mime.text import MIMEText
from db import SessionLocal, SeatNotification
from sqlalchemy import select
from dotenv import load_dotenv
import os


load_dotenv()


def send_email(to_email, seat_number, page_url, show_date, notification_id):
    password = os.getenv("app_password")

    # Configure your email settings
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = "rzh4321@gmail.com"
    confirmation_url = f"https://your-domain.com/unsubscribe/{notification_id}"

    msg = MIMEText(
        f"""
    Good news! Your requested AMC Theater Seat {seat_number} for your movie at {show_date} is now available!
    
    Click here to book: {page_url}
    
    If you successfully book this seat, please click here to stop notifications:
    
    """
    )

    msg["Subject"] = f"Seat {seat_number} is Available!"
    msg["From"] = sender_email
    msg["To"] = to_email

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(msg)
            print(f"Email sent successfully to {to_email}")
            return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False


def check_seats():
    # Get all notifications
    with SessionLocal() as session:
        notifications = session.execute(select(SeatNotification)).scalars().all()
        print(f'NOTIFS: {notifications}')

    driver = webdriver.Chrome()

    try:
        for notification in notifications:
            url = notification.page_url
            seat_number = notification.seat_number
            email = notification.user_email
            show_date = notification.show_date
            notification_id = notification.id

            driver.get(notification.url)

            # Wait for seats to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "button"))
            )
            buttons = driver.find_elements(By.TAG_NAME, "button")
            seat_buttons = [button for button in buttons if button.text.strip() == seat_number]

            if len(seat_buttons) == 0:
                print('cant find seat, clicking zoom now...')
                try:
                    zoom_button = driver.find_element(By.CSS_SELECTOR, ".rounded-full.bg-gray-400.p-4")
                    print('Zoom button found:', zoom_button is not None)
                    
                    zoom_button.click()
                    print('Clicked zoom button')
                                        
                    WebDriverWait(driver, 10).until(EC.staleness_of(seat_buttons[0])) if seat_buttons else None
                    
                    buttons = driver.find_elements(By.TAG_NAME, "button")
                    seat_buttons = [button for button in buttons if button.text.strip() == seat_number]
                    print('Seat buttons after zoom:', len(seat_buttons))
                    
                except NoSuchElementException:
                    print('Zoom button not found')
                
                if len(seat_buttons) == 0:
                    return {"error": "Seat number not found on this screen."}
                
            seat_button = seat_buttons[0]
            is_occupied = "cursor-not-allowed" in seat_button.get_attribute("class").split()
            print('Seat occupied status:', is_occupied)

            if is_occupied:
                send_email(
                    email, seat_number, url, show_date, notification_id
                )

    finally:
        driver.quit()


def run_scheduler():
    schedule.every(10).minutes.do(check_seats)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    # run_scheduler()
    check_seats()

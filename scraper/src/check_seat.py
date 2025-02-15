import asyncio
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import logging
import smtplib
from email.mime.text import MIMEText
from .db import SessionLocal, SeatNotification, Movie, Theater, Showtime
from sqlalchemy import select
from dotenv import load_dotenv
import os
import pytz
from sqlalchemy.sql import func
from datetime import datetime


load_dotenv()

logger = logging.getLogger(__name__)


def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # Use new headless mode
    chrome_options.add_argument("--window-size=1920,1080")  # Set window size
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument(
        "--disable-blink-features=AutomationControlled"
    )  # Hide automation
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )  # Set a regular Chrome user agent

    # Disable webdriver-specific flags
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--shm-size=2gb")

    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    # Add logging for debugging
    chrome_options.add_argument("--enable-logging")
    chrome_options.add_argument("--v=1")

    return webdriver.Chrome(options=chrome_options)


def send_email(
    to_email,
    seat_number,
    page_url,
    show_date,
    notification_id,
    movie,
    theater,
    showtime,
    is_specifically_requested,
    showtime_id,
):
    password = os.getenv("app_password")
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = "rzh4321@gmail.com"

    seat_notification_url = f"https://amc-seats-backend-production.up.railway.app/unsubscribe/{notification_id}"
    all_notifications_url = f"https://amc-seats-backend-production.up.railway.app/unsubscribe/{showtime_id}/{to_email}"

    if is_specifically_requested:
        intro = f"""Seat {seat_number} is now available"""
    else:
        intro = f"""A seat ({seat_number}) just opened up"""

    email_body = f"""
    Good news! {intro} for {movie} at {theater}!

    Movie Details:
    - Date: {show_date.strftime("%A, %B %d, %Y")}
    - Time: {showtime}
    - Seat: {seat_number}
    
    Click here to book your seat: {page_url}
    
    Important:
    1. If you successfully book seat {seat_number} or no longer want it, click here to stop notifications for seat {seat_number}:
    {seat_notification_url}
    
    2. If you want to unsubscribe from ALL notifications for this showing (if you were subscribed to multiple seats), click here:
    {all_notifications_url}
    
    Note: If you don't unsubscribe, you'll continue to receive notifications when this seat becomes available until the showtime has passed.
    """

    msg = MIMEText(email_body)
    msg["Subject"] = f"Seat {seat_number} Available - {movie} at {theater}"
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


def get_movie_info(notification):
    notification_id = notification.id
    email = notification.user_email
    seat_number = notification.seat_number
    last_notified = notification.last_notified
    if last_notified is not None:

        current_time = datetime.now(pytz.UTC)
        time_difference = current_time - last_notified
        should_be_notified = time_difference.total_seconds() > (
            12 * 3600
        )  # more than 12 hours
    else:
        should_be_notified = True

    is_specifically_requested = notification.is_specifically_requested
    showtime_id = notification.showtime_id
    with SessionLocal() as session:
        showtime_obj = (
            session.query(Showtime).filter(Showtime.id == showtime_id).first()
        )
        movie_id = showtime_obj.movie_id
        theater_id = showtime_obj.theater_id
        show_date = showtime_obj.show_date
        showtime = showtime_obj.showtime.strftime("%I:%M %p")
        url = showtime_obj.seating_url

        theater_obj = session.query(Theater).filter(Theater.id == theater_id).first()
        theater = theater_obj.name

        movie_obj = session.query(Movie).filter(Movie.id == movie_id).first()
        movie = movie_obj.name
        return (
            notification_id,
            email,
            seat_number,
            should_be_notified,
            is_specifically_requested,
            show_date,
            showtime,
            url,
            theater,
            movie,
            showtime_id,
        )


def check_seats():
    logger.info("Starting seat check...")
    # Get all notifications
    with SessionLocal() as session:
        notifications = session.execute(select(SeatNotification)).scalars().all()
        logger.info(f"Found {len(notifications)} notifications to process")

    driver = create_driver()

    try:
        for notification in notifications:
            try:
                (
                    notification_id,
                    email,
                    seat_number,
                    should_be_notified,
                    is_specifically_requested,
                    show_date,
                    showtime,
                    url,
                    theater,
                    movie,
                    showtime_id,
                ) = get_movie_info(notification)

                logger.info(
                    f'Checking seat {seat_number} for {movie} at {showtime} on {show_date.strftime("%A, %m-%d-%Y")} for {email}...'
                )

                driver.get(url)

                # Wait for seats to load
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "button"))
                )
                # Quick check if cookie dialog exists (using a short timeout)
                try:
                    WebDriverWait(driver, 1).until(
                        EC.presence_of_element_located(
                            (By.CLASS_NAME, "osano-cm-dialog")
                        )
                    )
                    # If we found the dialog, try to close it
                    try:
                        close_button = WebDriverWait(driver, 2).until(
                            EC.element_to_be_clickable(
                                (By.CLASS_NAME, "osano-cm-dialog__close")
                            )
                        )
                        driver.execute_script("arguments[0].click();", close_button)
                        logger.info("Clicked close button on cookie dialog")

                        # Wait for dialog to disappear
                        WebDriverWait(driver, 2).until(
                            EC.invisibility_of_element_located(
                                (By.CLASS_NAME, "osano-cm-dialog")
                            )
                        )
                    except Exception as e:
                        logger.error(f"Failed to close cookie dialog: {str(e)}")
                        # Fallback: remove dialog via JavaScript
                        driver.execute_script(
                            """
                            var dialog = document.querySelector('.osano-cm-dialog');
                            if (dialog) dialog.remove();
                        """
                        )
                        logger.info("Removed cookie dialog using JavaScript")
                except Exception:
                    logger.info("No cookie dialog found, proceeding with seat check")

                buttons = driver.find_elements(By.TAG_NAME, "button")
                seat_buttons = [
                    button for button in buttons if button.text.strip() == seat_number
                ]

                if len(seat_buttons) == 0:
                    try:
                        print("cant find seat, clicking zoom now...")
                        zoom_button = driver.find_element(
                            By.CSS_SELECTOR, ".rounded-full.bg-gray-400.p-4"
                        )
                        print("Zoom button found:", zoom_button is not None)

                        zoom_button.click()

                        # container = driver.find_element(By.CSS_SELECTOR, '#main .react-transform-wrapper')
                        # script = """
                        # const container = arguments[0];
                        # const rect = container.getBoundingClientRect();
                        # const centerX = rect.left + rect.width / 2;
                        # const centerY = rect.top + rect.height / 2;

                        # // Move mouse to center
                        # container.dispatchEvent(new MouseEvent('mousemove', {
                        #     bubbles: true,
                        #     clientX: centerX,
                        #     clientY: centerY
                        # }));

                        # // Trigger wheel event
                        # container.dispatchEvent(new WheelEvent('wheel', {
                        #     deltaY: -10000,
                        #     bubbles: true,
                        #     clientX: centerX,
                        #     clientY: centerY
                        # }));
                        # """

                        # driver.execute_script(script, container)

                        print("Clicked zoom button")

                        buttons = driver.execute_script(
                            f"""
    return Array.from(document.querySelectorAll('button'))
"""
                        )

                        seat_buttons = [
                            button
                            for button in buttons
                            if button.get_attribute("textContent").strip()
                            == seat_number
                        ]

                        print("Seat buttons after zoom:", len(seat_buttons))

                    except NoSuchElementException:
                        print("Zoom button not found")

                    if len(seat_buttons) == 0:
                        print(f"SEAT {seat_number} NOT FOUND ON SCREEN")
                        return {"error": "Seat number not found on this screen."}

                seat_button = seat_buttons[0]
                is_occupied = (
                    "cursor-not-allowed" in seat_button.get_attribute("class").split()
                )
                print("Seat occupied status:", is_occupied)

                if not is_occupied and should_be_notified:
                    email_sent = send_email(
                        email,
                        seat_number,
                        url,
                        show_date,
                        notification_id,
                        movie,
                        theater,
                        showtime,
                        is_specifically_requested,
                        showtime_id,
                    )
                    if email_sent:
                        with SessionLocal() as session:
                            notif = session.query(SeatNotification).filter(SeatNotification.id == notification_id).first()
                            notif.last_notified = func.now()
                            session.commit()
                            logger.info('updated last_notified after sending email')
                            logger.info(
                                f"Notification email sent to {email} for seat {seat_number}"
                            )
                    else:
                        logger.error(f"Failed to send email to {email}")
            except Exception as e:
                logger.error(f"Error processing notification: {str(e)}")
                continue  # Continue with next notification even if one fails
    except Exception as e:
        logger.error(f"Critical error in check_seats: {str(e)}")
    finally:
        driver.quit()

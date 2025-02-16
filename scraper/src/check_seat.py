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
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from .db import SessionLocal, SeatNotification, Movie, Theater, Showtime
from sqlalchemy import select
from dotenv import load_dotenv
import os
import pytz
from sqlalchemy.sql import func
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from multiprocessing import Pool


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
    <html>
    <head>
        <style>
            body {{
                font-family: 'Arial', sans-serif;
                line-height: 1.6;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                background-color: #ffffff;
            }}
            .header {{
                background-color: #d40000;
                color: white;
                padding: 20px;
                text-align: center;
                border-radius: 5px 5px 0 0;
            }}
            .content {{
                padding: 20px;
                background-color: #f9f9f9;
            }}
            .movie-details {{
                background-color: white;
                padding: 15px;
                border-radius: 5px;
                margin: 15px 0;
                border-left: 4px solid #d40000;
            }}
            .cta-button {{
                display: inline-block;
                background-color: #d40000;
                color: white;
                padding: 12px 25px;
                text-decoration: none;
                border-radius: 5px;
                margin: 10px 0;
            }}
            .footer {{
                background-color: #333333;
                color: white;
                padding: 15px;
                text-align: center;
                border-radius: 0 0 5px 5px;
                font-size: 0.9em;
            }}
            .unsubscribe {{
                color: #666666;
                font-size: 0.8em;
                text-align: center;
                margin-top: 15px;
            }}
            a {{
                color: #d40000;
                text-decoration: none;
            }}
            .footer a {{
                color: white;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>AMC Seat Alert!</h1>
            </div>
            <div class="content">
                <h2>Good news! {intro}</h2>
                
                <div class="movie-details">
                    <h3>{movie}</h3>
                    <p><strong>Theater:</strong> {theater}</p>
                    <p><strong>Date:</strong> {show_date.strftime("%A, %B %d, %Y")}</p>
                    <p><strong>Time:</strong> {showtime}</p>
                    <p><strong>Seat:</strong> {seat_number}</p>
                </div>

                <center>
                    <a href="{page_url}" class="cta-button">Book Your Seat Now</a>
                </center>

                <div class="unsubscribe">
                    <p>To stop notifications for seat {seat_number}:<br>
                    <a href="{seat_notification_url}">Unsubscribe from this seat</a></p>
                    
                    <p>To unsubscribe from ALL notifications for this showing:<br>
                    <a href="{all_notifications_url}">Unsubscribe from all seats</a></p>
                </div>
            </div>
            <div class="footer">
                <p>This is an automated notification for your requested seat alert.</p>
            </div>
        </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Seat {seat_number} Available - {movie} at {theater}"
    msg["From"] = sender_email
    msg["To"] = to_email

    # Attach both plain text and HTML versions
    text_part = MIMEText(email_body.replace("<br>", "\n"), "plain")
    html_part = MIMEText(email_body, "html")
    msg.attach(text_part)
    msg.attach(html_part)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(msg)
            logger.info(f"Email sent successfully to {to_email}")
            return True
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
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


def process_single_notification(notification_info):
    driver = create_driver()
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
        ) = notification_info
        logger.info(
            f'Checking seat {seat_number} for {movie} at {showtime} on {show_date.strftime("%A, %m-%d-%Y")} for {email}...'
        )
        seat_buttons = attempt_to_find_seat(driver, url, seat_number)

        if len(seat_buttons) == 0:
            logger.error(f"SEAT {seat_number} NOT FOUND ON SCREEN. TRYING AGAIN...")
            driver.quit()
            driver = create_driver()
            seat_buttons = attempt_to_find_seat(driver, url, seat_number)

            if len(seat_buttons) == 0:
                logger.error(
                    f"SEAT {seat_number} NOT FOUND ON SCREEN AFTER RETRY. SKIPPING THIS NOTIF..."
                )
                return

        seat_button = seat_buttons[0]
        is_occupied = "cursor-not-allowed" in seat_button.get_attribute("class").split()
        logger.info(f"Seat occupied status: {is_occupied}")

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
                    notif = (
                        session.query(SeatNotification)
                        .filter(SeatNotification.id == notification_id)
                        .first()
                    )
                    notif.last_notified = func.now()
                    session.commit()
                    logger.info("updated last_notified after sending email")
                    logger.info(
                        f"Notification email sent to {email} for seat {seat_number}"
                    )
            else:
                logger.error(f"Failed to send email to {email}")

    except Exception as e:
        logger.error(f"Critical error for notification: {str(e)}")
    finally:
        driver.quit()


def check_seats():
    logger.info("Starting seat check...")

    with SessionLocal() as session:
        notifications = session.execute(select(SeatNotification)).scalars().all()
        notification_count = len(notifications)
        logger.info(f"Found {notification_count} notifications to process")

        # only process as many as we need to
        notification_data = [get_movie_info(notif) for notif in notifications]

    try:
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(process_single_notification, data) 
                    for data in notification_data]
            
            for i, future in enumerate(as_completed(futures)):
                try:
                    future.result()  # Get the result (or exception)
                    logger.info(f"Completed {i + 1}/{notification_count} notifications")
                except Exception as e:
                    logger.error(f"Error processing notification: {str(e)}")
    except Exception as e:
        logger.error(f"Error in thread pool: {str(e)}")

def attempt_to_find_seat(driver, url, seat_number):
    driver.get(url)

    # Wait for seats to load
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "button"))
    )

    # Handle cookie dialog
    try:
        WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.CLASS_NAME, "osano-cm-dialog"))
        )
        try:
            close_button = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "osano-cm-dialog__close"))
            )
            driver.execute_script("arguments[0].click();", close_button)
            logger.info("Clicked close button on cookie dialog")
        except Exception as e:
            logger.error(f"Failed to close cookie dialog: {str(e)}")
            # use programmatic approach over selenium
            driver.execute_script(
                """
                var dialog = document.querySelector('.osano-cm-dialog');
                if (dialog) dialog.remove();
                """
            )
            logger.info("Removed cookie dialog using JavaScript")
    except Exception:
        logger.info("No cookie dialog found")

    # try to find seats without zooming
    buttons = driver.execute_script(
        f"""
            return Array.from(document.querySelectorAll('button'))
        """
    )

    seat_buttons = [
        button
        for button in buttons
        if button.get_attribute("textContent").strip() == seat_number
    ]
    # If no seat found, try zooming
    if len(seat_buttons) == 0:
        try:
            logger.error(f"Can't find seat {seat_number}, attempting zoom...")
            zoom_button = driver.find_element(
                By.CSS_SELECTOR, ".rounded-full.bg-gray-400.p-4"
            )
            logger.info(
                f"Zoom button for seat {seat_number} found: {zoom_button is not None}"
            )
            zoom_button.click()
            logger.info("Clicked zoom button")

            buttons = driver.execute_script(
                f"""
                    return Array.from(document.querySelectorAll('button'))
                """
            )

            seat_buttons = [
                button
                for button in buttons
                if button.get_attribute("textContent").strip() == seat_number
            ]

            logger.info(
                f"Seat buttons after zoom for seat {seat_number}: {len(seat_buttons)}"
            )

        except NoSuchElementException:
            logger.error("Zoom button not found")

    return seat_buttons

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
    date_string,
    notification_id,
    movie,
    theater,
    time_string,
    is_specifically_requested,
    showtime_id,
    first_time_notif,
):
    logger.info(f"SENT EMAIL=============================================\n")
    # 500 emails per day
    password = os.getenv("app_password")
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = "amcseatalert@gmail.com"

    seat_notification_url = f"https://amc-seats-backend-production.up.railway.app/unsubscribe/{notification_id}"
    all_notifications_url = f"https://amc-seats-backend-production.up.railway.app/unsubscribe/{showtime_id}/{to_email}"

    if is_specifically_requested:
        intro = f"""{'Reminder: ' if not first_time_notif else ''}Seat {seat_number} is now available"""
    else:
        intro = f"""{'Reminder: ' if not first_time_notif else ''}A seat ({seat_number}) just opened up"""

    email_body = f"""
    <html>
        <head>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
            </style>
        </head>
        <body style="background-color: #1A1A1A; color: #FFFFFF !important; font-family: 'Inter', sans-serif; line-height: 1.6; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #222222; border-radius: 12px; overflow: hidden;">
                <div style="background-color: #000000; padding: 24px; text-align: center; border-bottom: 2px solid #333333;">
                    <h1 style="color: #F5F5F5 !important; font-size: 28px; margin: 0;">AMC Seat Alert!</h1>
                </div>
                
                <div style="padding: 32px 24px;">
                    <h2 style="color: #E21836 !important; font-size: 24px; margin-bottom: 24px; text-align: center;">{intro}</h2>
                    
                    <div style="background-color: #2A2A2A; padding: 24px; border-radius: 8px; margin-bottom: 32px;">
                        <h3 style="color: #FFFFFF !important; font-size: 22px; margin-bottom: 16px; text-align: center;">{movie}</h3>
                        <p style="margin-bottom: 12px; color: #FFFFFF !important;">
                            <span style="color: #999999 !important;">Theater:</span> 
                            <span style="color: #FFFFFF !important;">{theater}</span>
                        </p>
                        <p style="margin-bottom: 12px; color: #FFFFFF !important;">
                            <span style="color: #999999 !important;">Date:</span> 
                            <span style="color: #FFFFFF !important;">{date_string}</span>
                        </p>
                        <p style="margin-bottom: 12px; color: #FFFFFF !important;">
                            <span style="color: #999999 !important;">Time:</span> 
                            <span style="color: #FFFFFF !important;">{time_string}</span>
                        </p>
                        <p style="margin-bottom: 12px; color: #FFFFFF !important;">
                            <span style="color: #999999 !important;">Seat:</span> 
                            <span style="color: #FFFFFF !important;">{seat_number}</span>
                        </p>
                    </div>

                    <div style="text-align: center; margin-bottom: 32px;">
                        <a href="{page_url}" style="display: inline-block; background-color: #E21836; color: #FFFFFF !important; padding: 16px 32px; text-decoration: none; border-radius: 8px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Book Your Seat Now</a>
                    </div>

                    <div style="border-top: 1px solid #333333; padding-top: 24px;">
                        <p style="color: #999999 !important; margin-bottom: 16px; text-align: center;">Booked your seat or want to stop notifications?</p>
                        
                        <div style="text-align: center; margin-bottom: 16px;">
                            <a href="{seat_notification_url}" style="display: inline-block; background-color: #333333; color: #FFFFFF !important; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-size: 14px; margin-bottom: 12px;">Unsubscribe from Seat {seat_number}</a>
                        </div>
                        
                        <div style="text-align: center;">
                            <a href="{all_notifications_url}" style="display: inline-block; background-color: #333333; color: #FFFFFF !important; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-size: 14px;">Unsubscribe from this showing</a>
                        </div>
                    </div>
                </div>
                
                <div style="background-color: #000000; padding: 16px; text-align: center;">
                    <p style="color: #666666 !important; font-size: 12px; margin: 0;">This email was sent automatically. Do not reply.</p>
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
            # logger.info(f"Email sent successfully to {to_email}")
            return True
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False


def get_movie_info(notification):
    notification_id = notification.id
    email = notification.user_email
    seat_number = notification.seat_number
    last_notified = notification.last_notified
    first_time_notif = True
    if last_notified is not None:

        current_time = datetime.now(pytz.UTC)
        time_difference = current_time - last_notified
        should_be_notified = time_difference.total_seconds() > (
            6 * 3600
        )  # more than 6 hours
        first_time_notif = False
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

        url = showtime_obj.seating_url

        theater_obj = session.query(Theater).filter(Theater.id == theater_id).first()
        theater = theater_obj.name
        timezone = theater_obj.timezone
        movie_datetime = showtime_obj.showtime
        # Convert UTC to specified timezone
        tz = pytz.timezone(timezone)
        local_datetime = movie_datetime.astimezone(tz)

        # Format date like "Sunday, February 16, 2025"
        date_string = local_datetime.strftime("%A, %B %d, %Y")

        # Format time like "7:30 pm"
        time_string = local_datetime.strftime("%I:%M %p").lstrip("0").lower()

        movie_obj = session.query(Movie).filter(Movie.id == movie_id).first()
        movie = movie_obj.name
        return (
            notification_id,
            email,
            seat_number,
            should_be_notified,
            is_specifically_requested,
            date_string,
            time_string,
            url,
            theater,
            movie,
            showtime_id,
            first_time_notif,
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
            date_string,
            time_string,
            url,
            theater,
            movie,
            showtime_id,
            first_time_notif,
        ) = notification_info
        logger.info(
            f"Checking seat {seat_number} for {movie} at {date_string} on {time_string} for {email}..."
        )
        seat_buttons = attempt_to_find_seat(driver, url, seat_number)

        if len(seat_buttons) == 0:
            # logger.error(f"SEAT {seat_number} NOT FOUND ON SCREEN. TRYING AGAIN...")
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
        logger.info(f"Seat {seat_number} is available: {not is_occupied}")

        if not is_occupied and should_be_notified:
            email_sent = send_email(
                email,
                seat_number,
                url,
                date_string,
                notification_id,
                movie,
                theater,
                time_string,
                is_specifically_requested,
                showtime_id,
                first_time_notif,
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
                    # logger.info("updated last_notified after sending email")
                    # logger.info(
                    #     f"Notification email sent to {email} for seat {seat_number}"
                    # )
            else:
                logger.error(f"Failed to send email to {email}")

    except Exception as e:
        logger.error(f"Critical error for notification: {str(e)}")
    finally:
        driver.quit()


def check_seats():
    logger.info("Starting seat check...")

    with SessionLocal() as session:
        # first fetch all notifications from DB
        notifications = session.execute(select(SeatNotification)).scalars().all()
        notification_count = len(notifications)
        logger.info(f"Found {notification_count} notifications to process")

    # process notifications in parallel using a thread pool
    # and immediately send them to process_single_notification
    try:
        max_workers_info = 4  # For get_movie_info
        max_workers_process = 4  # For process_single_notification

        with ThreadPoolExecutor(
            max_workers=max_workers_info
        ) as info_executor, ThreadPoolExecutor(
            max_workers=max_workers_process
        ) as process_executor:

            # call get_movie_info on each notif, submit all jobs to thread pool
            # executor.submit() is non blocking, it just queues get_movie_info quickly and it
            # start asynchronously
            info_futures = {
                info_executor.submit(get_movie_info, notif): notif
                for notif in notifications
            }

            # As soon as get_movie_info returns a result, pass it to process_single_notification
            # as_completed() is a generator that yields future objects as soon as they are done
            process_futures = []
            for future in as_completed(info_futures):
                try:
                    # future.result() wont block bc as_completed() only gives us finished futures
                    data = future.result()
                    # Submit processing job
                    # again, submit() is nonblocking and just queues the job to be executed by another
                    # thread. Append the returned future to process_futures so we can track and wait for
                    # it later
                    pf = process_executor.submit(process_single_notification, data)
                    process_futures.append(pf)
                except Exception as e:
                    logger.error(f"Failed to get movie info: {str(e)}")

            # Wait for all processing to complete
            # as soon as a future in process_futures is complete, log it out
            for i, future in enumerate(as_completed(process_futures)):
                try:
                    future.result()
                    logger.info(f"Completed {i + 1}/{notification_count} notifications")
                except Exception as e:
                    logger.error(f"Error processing notification: {str(e)}")

    except Exception as e:
        logger.error(f"Error in thread pools: {str(e)}")


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
            # logger.info("Clicked close button on cookie dialog")
        except Exception as e:
            # logger.error(f"Failed to close cookie dialog: {str(e)}")
            # use programmatic approach over selenium
            driver.execute_script(
                """
                var dialog = document.querySelector('.osano-cm-dialog');
                if (dialog) dialog.remove();
                """
            )
            # logger.info("Removed cookie dialog using JavaScript")
    except Exception:
        # logger.info("No cookie dialog found")
        pass

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
            # logger.error(f"Can't find seat {seat_number}, attempting zoom...")
            zoom_button = driver.find_element(
                By.CSS_SELECTOR, ".rounded-full.bg-gray-400.p-4"
            )
            # logger.info(
            #     f"Zoom button for seat {seat_number} found: {zoom_button is not None}"
            # )
            zoom_button.click()
            # logger.info("Clicked zoom button")

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

            # logger.info(
            #     f"Seat buttons after zoom for seat {seat_number}: {len(seat_buttons)}"
            # )

        except NoSuchElementException:
            logger.error("Zoom button not found")

    return seat_buttons

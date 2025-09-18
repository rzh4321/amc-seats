import logging
import os
import time
import random
from collections import defaultdict
from datetime import datetime

import pytz
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.sql import func

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .db import SessionLocal, SeatNotification, Movie, Theater, Showtime

load_dotenv()

logger = logging.getLogger(__name__)


# Selenium timeouts (seconds):
# - PAGE_LOAD_TIMEOUT: max time to wait for a full page navigation.
# - ELEMENT_WAIT_TIMEOUT: max time explicit waits will wait for specific DOM elements.
PAGE_LOAD_TIMEOUT = 30
ELEMENT_WAIT_TIMEOUT = 15

# Whether to run the browser headless:
# - Non-headless is less likely to be fingerprinted as a bot, but requires a display and is slower.
# - If you must run headless in production, consider using legacy "--headless" and keep flags minimal.
RUN_HEADLESS = True  # Set to True if your environment requires headless mode.


def create_driver():
    """
    Create and return a configured Selenium Chrome WebDriver.

    Design choices:
    - We prefer running non-headless to reduce bot signals. If you must run headless, set
      RUN_HEADLESS = True and use the minimal set of flags.
    - Keep flags to a minimum to avoid automation fingerprints.
    - Use a consistent user-agent that matches your Chrome build.
    - Set a page load timeout to avoid hanging indefinitely on navigation.
    """
    chrome_options = Options()

    if RUN_HEADLESS:
        # Use legacy headless for better compatibility:
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1920,1080")

    else:
        chrome_options.add_argument("--window-size=1920,1080")

    # If running as root (e.g., in a container), Chrome requires --no-sandbox.
    # If you are not root, you can remove this.
    chrome_options.add_argument("--no-sandbox")

    # If your container has very small /dev/shm (common on Docker), Chrome can crash. Prefer to
    # increase /dev/shm size (e.g., docker run --shm-size=2g). If not possible, enable this:
    # chrome_options.add_argument("--disable-dev-shm-usage")

    # chrome_options.add_argument(
    #     "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    #     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    # )
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    )


    service = Service()

    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Set a global navigation timeout for get() and associated loads.
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)

    return driver


def send_email(
    to_email: str,
    seat_number: str,
    page_url: str,
    date_string: str,
    notification_id: int,
    movie: str,
    theater: str,
    time_string: str,
    is_specifically_requested: bool,
    showtime_id: int,
    first_time_notif: bool,
) -> bool:
    """
    Send a styled HTML email to the user informing them a seat is available.

    Inputs:
    - to_email: recipient email address.
    - seat_number: e.g., "K26".
    - page_url: booking page URL so the user can click to purchase.
    - date_string / time_string: human-friendly local date/time for the show.
    - notification_id: used for per-seat unsubscribe link.
    - movie / theater: context info for the email body.
    - is_specifically_requested: whether the seat was specifically requested vs. general alert.
    - showtime_id: used for per-showtime unsubscribe link.
    - first_time_notif: whether this is the first time we notify (affects email intro wording).

    Returns:
    - True on success, False if sending fails (e.g., SMTP error).
    """
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    logger.info("SENDING EMAIL (attempt)...")

    # SMTP credentials and sender identity:
    password = os.getenv("app_password")  # App password from environment (.env)
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = "amcseatalert@gmail.com"

    # Unsubscribe links for user convenience:
    seat_notification_url = f"https://amc-seats-backend.onrender.com/unsubscribe/{notification_id}"
    all_notifications_url = f"https://amc-seats-backend.onrender.com/unsubscribe/{showtime_id}/{to_email}"

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

    # Build a multi-part email so some clients can fall back to plain text.
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Seat {seat_number} Available - {movie} at {theater}"
    msg["From"] = sender_email
    msg["To"] = to_email

    # Provide both plain text (fallback) and HTML (primary) versions.
    text_part = MIMEText(email_body.replace("<br>", "\n"), "plain")
    html_part = MIMEText(email_body, "html")
    msg.attach(text_part)
    msg.attach(html_part)

    # SMTP send with TLS:
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Upgrade connection to secure TLS
            server.login(sender_email, password)
            server.send_message(msg)
            return True
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False


def _load_all_notifications():
    """
    Load all SeatNotification rows from the database in one query.

    Returns:
    - A list of SeatNotification SQLAlchemy model instances.
    """
    with SessionLocal() as session:
        notifications = session.execute(select(SeatNotification)).scalars().all()
    return notifications


def _enrich_showtime_info(showtime_id: int):
    """
    Load additional data for a showtime, including:
    - seating URL, movie name, theater name, local time zone info,
      human-friendly date and time strings.

    Returns:
    - A dict with keys: url, movie, theater, timezone, date_string, time_string, showtime_obj
    - None if showtime not found.
    """
    with SessionLocal() as session:
        showtime_obj = session.query(Showtime).filter(Showtime.id == showtime_id).first()
        if not showtime_obj:
            return None

        theater_obj = session.query(Theater).filter(Theater.id == showtime_obj.theater_id).first()
        movie_obj = session.query(Movie).filter(Movie.id == showtime_obj.movie_id).first()

        url = showtime_obj.seating_url
        theater = theater_obj.name if theater_obj else "Unknown Theater"
        timezone = theater_obj.timezone if theater_obj else "UTC"

        # Convert the showtime (assumed stored in UTC) to the theater's local timezone
        # to display dates/times users expect.
        movie_datetime = showtime_obj.showtime
        tz = pytz.timezone(timezone)
        local_datetime = movie_datetime.astimezone(tz)

        # Format:
        # - Date: "Sunday, February 16, 2025"
        # - Time: "7:30 pm" (lowercase am/pm, no leading zero)
        date_string = local_datetime.strftime("%A, %B %d, %Y")
        time_string = local_datetime.strftime("%I:%M %p").lstrip("0").lower()

        movie = movie_obj.name if movie_obj else "Unknown Movie"

        return {
            "url": url,
            "movie": movie,
            "theater": theater,
            "timezone": timezone,
            "date_string": date_string,
            "time_string": time_string,
            "showtime_obj": showtime_obj,
        }


def _should_notify(last_notified):
    """
    Decide whether we should notify a user again.

    Rule:
    - If never notified: notify now (first_time=True).
    - Else: only notify if at least 6 hours have passed since last notification.

    Returns:
    - (should_notify: bool, first_time_notif: bool)
    """
    if last_notified is None:
        return True, True  # never notified before
    current_time = datetime.now(pytz.UTC)
    time_difference = current_time - last_notified
    if time_difference.total_seconds() > 6 * 3600:
        return True, False  # notify again, but it's not the first time
    return False, False  # too soon to re-notify


def _update_last_notified(notification_id: int):
    """
    Update the last_notified timestamp for a SeatNotification to NOW().

    Called after a successful email send.
    """
    with SessionLocal() as session:
        notif = session.query(SeatNotification).filter(SeatNotification.id == notification_id).first()
        if notif:
            notif.last_notified = func.now()
            session.commit()




def _detect_block_page(driver) -> bool:
    """
    Heuristic to detect whether the current page is a "blocked/banned" interstitial.

    Approach:
    - Read the page body text and look for phrases like "banned" or "temporarily from accessing".
    - This is intentionally simple; adjust with more precise selectors or titles if needed.

    Returns:
    - True if a block page is likely shown; False otherwise.
    """
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        if "banned" in body_text or "temporarily from accessing" in body_text:
            return True
        return False
    except Exception:
        # If we fail to read the body (rare), assume no block to avoid false positives.
        return False


def _close_cookie_dialog_if_present(driver):
    """
    Attempt to close a cookie/policy dialog if present.

    Strategy:
    - Look for the presence of a known dialog class "osano-cm-dialog".
    - If present, attempt to click its close button (class "osano-cm-dialog__close").
    - If not clickable, we ignore (do not forcibly remove the DOM with JS to avoid suspicious behavior).
    """
    try:
        # First, detect if the dialog exists at all (short wait).
        WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.CLASS_NAME, "osano-cm-dialog"))
        )
        # If present, try to find and click the close button safely.
        try:
            close_button = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "osano-cm-dialog__close"))
            )
            # Use JS click (often more reliable for overlay buttons).
            driver.execute_script("arguments[0].click();", close_button)
            # Small human-like pause to let the DOM settle.
            time.sleep(random.uniform(0.1, 0.3))
        except Exception:
            # If we can't click, we simply proceed without closing.
            # Avoid DOM surgery (removing the dialog) to reduce bot signals.
            pass
    except Exception:
        # Dialog not present; nothing to do.
        pass


def _parse_available_seats(driver):
    """
    Parse all seat cells on the current seating page and determine which are occupied vs available.

    Assumptions (based on your prior code):
    - Seat cells are represented by elements matching 'div[role="gridcell"]'.
    - The text content of the cell is the seat label (e.g., "K26").
    - Occupancy is indicated by a CSS class on a direct child element named "cursor-not-allowed".
      If present, the seat is occupied; otherwise, it’s available.

    Returns:
    - (all_labels, occupied_labels)
      * all_labels: a set of all seat labels found (strings).
      * occupied_labels: a set of seat labels that are currently occupied.

    Raises:
    - TimeoutException if the seat grid doesn’t appear within ELEMENT_WAIT_TIMEOUT.
    """
    # Wait until at least one seat cell appears. This ensures the seat map is loaded.
    WebDriverWait(driver, ELEMENT_WAIT_TIMEOUT).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="gridcell"]'))
    )

    # Close cookie dialog if it covers the UI; ignore silently if not present.
    _close_cookie_dialog_if_present(driver)

    # Gather all seat cell elements.
    # Note: We use Selenium's find_elements to get WebElement references we can query safely.
    cells = driver.find_elements(By.CSS_SELECTOR, 'div[role="gridcell"]')

    # Prepare sets to record labels.
    all_labels = set()
    occupied = set()

    # Iterate through each seat cell and extract label and occupancy.
    for c in cells:
        label = (c.text or "").strip()
        if not label:
            # Some gridcells might be decorative or empty (no seat label); skip those.
            continue
        all_labels.add(label)
        try:
            # Many seat cells have a single child whose class names indicate availability.
            child = c.find_element(By.XPATH, "./*")
            classes = (child.get_attribute("class") or "").split()
            if "cursor-not-allowed" in classes:
                occupied.add(label)
        except Exception:
            # If structure differs for some cells (e.g., no child), we assume it's not "occupied" by
            # this particular rule. If needed, add more heuristics here.
            pass

    return all_labels, occupied


def _notify_for_showtime(driver, showtime_id: int, url: str, notif_group, meta_info):
    """
    For a single showtime:
    - Navigate to its seating URL.
    - Detect block page; if blocked, return early
    - Parse all seats and compute which are available.
    - For each user's notification in notif_group:
      * Decide if they should be notified (rate-limited by last_notified).
      * If their seat is available, send email and update last_notified.

    Inputs:
    - driver: Selenium WebDriver (shared for the entire sweep).
    - showtime_id: integer ID for the showtime.
    - url: seating page URL.
    - notif_group: list of SeatNotification rows for this showtime.
    - meta_info: dict with movie/theater/date/time strings (from _enrich_showtime_info).

    Returns:
    - (emails_sent: int, was_blocked: bool)
    """
    emails_sent = 0
    was_blocked = False

    # Navigate to the seating page. If navigation fails (timeout/network), we log and skip.
    try:
        driver.get(url)
    except Exception as e:
        logger.error(f"Navigation failed for {url}: {e}")
        return emails_sent, was_blocked

    # Short, random human-like pause after navigation to reduce "bot-like" patterns and allow
    # any async UI elements to stabilize slightly.
    time.sleep(random.uniform(0.2, 0.6))

    # Check if the server returned a ban/blocked interstitial. If so, do not continue parsing.
    if _detect_block_page(driver):
        logger.warning("Block/ban page detected; backing off.")
        was_blocked = True
        return emails_sent, was_blocked

    # Parse the seat grid to find which labels exist and which are occupied.
    try:
        all_labels, occupied = _parse_available_seats(driver)
    except Exception as e:
        logger.error(f"Failed to parse seats for {url}: {e}")
        return emails_sent, was_blocked

    # Available seats are simply "all labels" minus "occupied labels".
    available = all_labels - occupied

    # Fan-out notifications to all users for this showtime:
    for n in notif_group:
        # Decide if we're allowed to notify this user now based on last_notified timestamp.
        should_notify, first_time_notif = _should_notify(n.last_notified)
        if not should_notify:
            continue  # Skip this user; we'll try again after 6-hour window.

        seat_label = n.seat_number
        if seat_label in available:
            # Seat is currently available: send email.
            logger.info(f"Seat {seat_label} is available for {n.user_email} on showtime {showtime_id}")
            ok = send_email(
                n.user_email,
                seat_label,
                url,
                meta_info["date_string"],
                n.id,
                meta_info["movie"],
                meta_info["theater"],
                meta_info["time_string"],
                n.is_specifically_requested,
                showtime_id,
                first_time_notif,
            )
            if ok:
                # Record the notification time to implement the "6-hour cool-down per user" rule.
                _update_last_notified(n.id)
                emails_sent += 1
            else:
                logger.error(f"Failed to send email to {n.user_email}")
        else:
            # Seat requested by this user is not currently available.
            logger.info(f"Seat {seat_label} not available for showtime {showtime_id}")

    return emails_sent, was_blocked



def check_seats():
    """
    Entry point for a single "sweep" using the grouped strategy:

    Steps:
    1) Load all SeatNotification rows.
    2) Group them by showtime_id (so we fetch each URL once).
    3) Build per-showtime metadata (URL, movie/theater names, local date/time strings).
    4) Create a single WebDriver instance to be reused for all showtimes.
    5) Iterate showtimes in randomized order:
       a) Fetch the page, parse seats once, fan-out notifications to all users for that showtime.
    6) Quit the WebDriver at the end.

    """
    logger.info("Starting grouped seat check...")

    # Fetch all current notifications from the DB.
    notifications = _load_all_notifications()
    if not notifications:
        logger.info("No notifications to process.")
        return

    # Group notifications by showtime_id.
    grouped = defaultdict(list)
    for n in notifications:
        grouped[n.showtime_id].append(n)

    logger.info(f"Found {len(notifications)} notifications across {len(grouped)} showtimes.")

    # Prepare metadata and URLs for each showtime. Skip any showtime that lacks URL or metadata.
    showtime_meta = {}
    url_by_showtime = {}
    for showtime_id in grouped.keys():
        meta = _enrich_showtime_info(showtime_id)
        if not meta or not meta.get("url"):
            logger.warning(f"Skipping showtime {showtime_id}: missing metadata or URL")
            continue
        showtime_meta[showtime_id] = meta
        url_by_showtime[showtime_id] = meta["url"]


    # Create a single WebDriver instance for the entire sweep.
    driver = None
    try:
        driver = create_driver()

        # Process showtimes in a randomized order to avoid deterministic request bursts on the same URLs.
        showtime_ids = list(url_by_showtime.keys())
        random.shuffle(showtime_ids)

        for i, showtime_id in enumerate(showtime_ids):
            meta = showtime_meta[showtime_id]
            url = meta["url"]
            notif_group = grouped[showtime_id]         
            first_showtime = (i == 0)   

            # wait a minute between every page navigation except the first
            if not first_showtime:
                logger.info(f"Waiting 20 seconds before next page fetch...")
                time.sleep(20)

            # Fetch and notify for this showtime.
            emails_sent, was_blocked = _notify_for_showtime(driver, showtime_id, url, notif_group, meta)

            if was_blocked:
                logger.warning(f"Breaking due to block.")
                break

        logger.info(f"Completed grouped sweep.")

    finally:
        # Ensure the browser process is terminated even if we hit exceptions.
        try:
            if driver:
                driver.quit()
        except Exception:
            pass

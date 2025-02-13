import asyncio
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from apscheduler.schedulers.blocking import BlockingScheduler
import logging
import smtplib
from email.mime.text import MIMEText
from db import SessionLocal, SeatNotification
from sqlalchemy import select
from dotenv import load_dotenv
import os


load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')  # Use new headless mode
    chrome_options.add_argument('--window-size=1920,1080')  # Set window size
    chrome_options.add_argument('--start-maximized')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')  # Hide automation
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')  # Set a regular Chrome user agent

    # Disable webdriver-specific flags
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)


    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--shm-size=2gb')

    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-infobars')


    
    return webdriver.Chrome(options=chrome_options)

def send_email(to_email, seat_number, page_url, show_date, notification_id):
    password = os.getenv("app_password")

    # Configure your email settings
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = "rzh4321@gmail.com"
    confirmation_url = f"https://amc-seats-backend-production.up.railway.app/unsubscribe/{notification_id}"

    msg = MIMEText(
        f"""
    Good news! Your requested AMC Theater Seat {seat_number} for your movie at {show_date.strftime("%A, %m-%d-%Y")} is now available!
    
    Click here to book: {page_url}
    
    If you successfully book this seat, please click here to stop notifications:
    {confirmation_url}
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
    logger.info("Starting seat check...")
    # Get all notifications
    with SessionLocal() as session:
        notifications = session.execute(select(SeatNotification)).scalars().all()
        logger.info(f'Found {len(notifications)} notifications to process')

    driver = create_driver()

    try:
        for notification in notifications:
            try:
                url = notification.url
                seat_number = notification.seat_number
                email = notification.user_email
                show_date = notification.show_date
                notification_id = notification.id

                logger.info(f'Checking seat {seat_number} for {email}...')

                driver.get(url)

                # Wait for seats to load
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "button"))
                )
                    # Quick check if cookie dialog exists (using a short timeout)
                try:
                    WebDriverWait(driver, 1).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "osano-cm-dialog"))
                    )
                    # If we found the dialog, try to close it
                    try:
                        close_button = WebDriverWait(driver, 2).until(
                            EC.element_to_be_clickable((By.CLASS_NAME, "osano-cm-dialog__close"))
                        )
                        driver.execute_script("arguments[0].click();", close_button)
                        logger.info("Clicked close button on cookie dialog")
                        
                        # Wait for dialog to disappear
                        WebDriverWait(driver, 2).until(
                            EC.invisibility_of_element_located((By.CLASS_NAME, "osano-cm-dialog"))
                        )
                    except Exception as e:
                        logger.error(f"Failed to close cookie dialog: {str(e)}")
                        # Fallback: remove dialog via JavaScript
                        driver.execute_script("""
                            var dialog = document.querySelector('.osano-cm-dialog');
                            if (dialog) dialog.remove();
                        """)
                        logger.info("Removed cookie dialog using JavaScript")
                except Exception:
                    logger.info("No cookie dialog found, proceeding with seat check")

                buttons = driver.find_elements(By.TAG_NAME, "button")
                seat_buttons = [button for button in buttons if button.text.strip() == seat_number]

                if len(seat_buttons) == 0:
                    try:
                        print('cant find seat, clicking zoom now...')
                        zoom_button = driver.find_element(By.CSS_SELECTOR, ".rounded-full.bg-gray-400.p-4")
                        print('Zoom button found:', zoom_button is not None)
                        
                        zoom_button.click()                  
                        print('Clicked zoom button')

                        buttons = driver.find_elements(By.TAG_NAME, "button")
                        
                        seat_buttons = [button for button in buttons if button.text.strip() == seat_number]
                        print('Seat buttons after zoom:', len(seat_buttons))
                        
                    except NoSuchElementException:
                        print('Zoom button not found')


                    
                    
                    if len(seat_buttons) == 0:
                        print(f'SEAT {seat_number} NOT FOUND ON SCREEN')
                        return {"error": "Seat number not found on this screen."}
                    
                seat_button = seat_buttons[0]
                is_occupied = "cursor-not-allowed" in seat_button.get_attribute("class").split()
                print('Seat occupied status:', is_occupied)

                if not is_occupied:
                    email_sent = send_email(
                        email, seat_number, url, show_date, notification_id
                    )
                    if email_sent:
                        logger.info(f'Notification email sent to {email} for seat {seat_number}')
                    else:
                        logger.error(f'Failed to send email to {email}')
            except Exception as e:
                logger.error(f'Error processing notification: {str(e)}')
                continue  # Continue with next notification even if one fails
    except Exception as e:
        logger.error(f'Critical error in check_seats: {str(e)}')
    finally:
        driver.quit()


def main():
    scheduler = BlockingScheduler()
    # Run check_seats immediately when starting
    logger.info("Running initial check...")
    check_seats()
    # Schedule job to run every 5 minutes
    scheduler.add_job(check_seats, 'interval', minutes=5)
    
    logger.info("Starting scheduler...")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")

if __name__ == "__main__":
    main()

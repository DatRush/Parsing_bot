import logging
import psycopg2
import re
import time
from bs4 import BeautifulSoup
from config import DATABASE, LOGGING_CONFIG, TIMEOUTS, EMAIL
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailErrorHandler(logging.Handler):
    # Initializes the EmailErrorHandler to send logs via email.
    def __init__(self, from_email, to_email, email_password, smtp_server='smtp.gmail.com', smtp_port=587):
        super().__init__()
        self.from_email = from_email
        self.to_email = to_email
        self.email_password = email_password
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port

    # Sends an email with the log record as the message body when an error is logged.
    def emit(self, record):
        try:
            message = MIMEMultipart()
            message['From'] = self.from_email
            message['To'] = self.to_email
            message['Subject'] = "Ошибка в приложении"

            body = self.format(record)
            message.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.from_email, self.email_password)
            server.sendmail(self.from_email, self.to_email, message.as_string())
            server.quit()
        except Exception as e:
            pass

def setup_logging():
    # Configures logging with multiple handlers (file and email).
    logger = logging.getLogger('parsing_kolesa')
    logger.setLevel(LOGGING_CONFIG['level'])

    formatter = logging.Formatter(LOGGING_CONFIG['format'])

    info_handler = logging.FileHandler(LOGGING_CONFIG['info_file'])
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)

    error_handler = logging.FileHandler(LOGGING_CONFIG['error_file'])
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    
    email_handler = EmailErrorHandler(**EMAIL)
    email_handler.setLevel(logging.ERROR)
    email_handler.setFormatter(formatter)

    logger.addHandler(info_handler)
    logger.addHandler(error_handler)
    logger.addHandler(email_handler)

    return logger

def connect_db():
    # Establishes a connection to the database using parameters from the config.
    return psycopg2.connect(**DATABASE)
    
def try_load_page(page, url, logger):
    # Attempts to load a web page with retries and logs errors.
    max_attempts = TIMEOUTS['max_attempts']
    for attempt in range(max_attempts):
        try:
            page.goto(url, timeout=TIMEOUTS['page_load'], wait_until="domcontentloaded")
            return True  
        except Exception as e:
            logger.error(f"Ошибка загрузки страницы {url}: {e}, попытка {attempt + 1} из {max_attempts}")
            if attempt < max_attempts - 1:
                time.sleep(TIMEOUTS['retry_sleep'])  
            else:
                logger.error(f"Не удалось загрузить страницу {url} после {max_attempts} попыток.")
                return False
    return False
    
    
def convert_to_boolean(text):
    # Converts text to boolean.
    if text == "Да":
        return True
    elif text == "Нет":
        return False
    else:
        return None

    
def insert_ad(ad_data_list, conn):
    # Inserts multiple ads into the database using a single transaction.
    with conn.cursor() as cur:
        query = """
        INSERT INTO ads (id_car, title, year, price, city, seller_comment, generation, body_type, engine_volume, transmission, drive_type, wheel_side, color, customs_cleared, url, insert_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id_car) DO NOTHING;
        """
        data_tuples = [
            (
                extract_id_from_url(ad['url']),
                ad['title'], ad['year'], ad['price'], ad['city'],
                ad['seller_comment'],
                ad['generation'], ad['body_type'], ad['engine_volume'],
                ad['transmission'], ad['drive_type'], ad['wheel_side'],
                ad['color'], convert_to_boolean(ad['customs_cleared']), ad['url'],
                ad['insert_date']
            ) for ad in ad_data_list
        ]
        cur.executemany(query, data_tuples)
        conn.commit()
    
    
    
def clean_comment(comment_html):
    # Cleans HTML content from the seller comment and returns plain text.
    soup = BeautifulSoup(comment_html, 'html.parser')
    comment_text = soup.get_text(separator=' ', strip=True) 
    return comment_text


def is_url_in_set(id_car, existing_ids):
    # Checks if a car ID is already recorded by checking against a set of existing IDs.
    return id_car in existing_ids

def extract_id_from_url(url):
    # Extracts the numeric ID from a URL using regular expressions.
    match = re.search(r'/(\d+)', url)
    return match.group(1) if match else None

def fetch_existing_ids(cur):
    # Fetches all existing car IDs from the database to check for duplicates.
    cur.execute("SELECT id_car FROM ads")  
    rows = cur.fetchall()
    return {row[0] for row in rows}

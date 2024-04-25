DATABASE = {
    "dbname": "kolesa",
    "user": "your_username",
    "password": "your_password",
    "host": "localhost"
}

BASE_URL = "https://kolesa.kz"
DEFAULT_TIMEOUT = 80000
SLEEP_INTERVAL = 7200  

LOGGING_CONFIG = {
    "level": "DEBUG",
    "format": "%(asctime)s - %(levelname)s - %(message)s",
    "info_file": "logs/info.log",
    "error_file": "logs/error.log"
}

TIMEOUTS = {
    "page_load": 90000,
    "retry_sleep": 10,
    "max_attempts": 3
}

EMAIL = {
    "from_email": "your_email@example.com",
    "to_email": "recipient_email@example.com",
    "email_password": "your_email_password"
}

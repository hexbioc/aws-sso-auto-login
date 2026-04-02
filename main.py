import os
import re
import subprocess
import sys
import json
import time


from selenium.webdriver.common.by import By
from pyotp import TOTP
from dotenv import load_dotenv


from logger import logger
from executor import SeleniumExecutor
from profiler import function_profiler

from datetime import datetime, timedelta, UTC

load_dotenv()

AWS_BINARY = os.getenv("AWS_BINARY")
AWS_STS_PROFILE = os.getenv("AWS_STS_PROFILE")
AWS_SSO_SESSION = os.getenv("AWS_SSO_SESSION")

AWS_SSO_CACHE_PATH = os.path.expanduser("~/.aws/sso/cache")
TOKEN_EXPIRY_THRESHOLD = timedelta(minutes=10)

AD_URL_PREFIX = "https://login.microsoftonline.com"


@function_profiler.profile
def get_token_expiry() -> datetime:
    fallback_timestamp = datetime.now(UTC) - timedelta(days=1)

    if not os.path.isdir(AWS_SSO_CACHE_PATH):
        return fallback_timestamp

    # Check the cached JSON files for the presence of an access token
    for f in os.listdir(AWS_SSO_CACHE_PATH):
        if not f.lower().endswith(".json"):
            continue

        with open(os.path.join(AWS_SSO_CACHE_PATH, f), "r") as fp:
            data = json.load(fp)

            if "accessToken" not in data or "expiresAt" not in data:
                continue

            return datetime.fromisoformat(data["expiresAt"])

    # If a token is not found, return a timestamp from the past
    return fallback_timestamp


def get_executor():
    headless = os.environ.get("RENDER_BROWSER") != "1"
    executor = SeleniumExecutor(headless=headless)

    return executor


def microsoft_active_directory_check():
    logger.info("Checking if Microsoft AD login is required")

    url = os.getenv("AD_CHECK_URL", "https://google.com")
    executor = None

    try:
        executor = get_executor()
        executor.open(url)

        time.sleep(2)

        # If a general internet URL opens without redirect to login, AD is already active
        if not executor.driver.current_url.startswith(AD_URL_PREFIX):
            logger.info("Microsoft AD already logged in, nothing to do")
            return  # Nothing to do

        # Have to login into microsoft AD
        logger.info("Beginning Microsoft AD login")
        microsoft_login(executor)
        logger.info("Microsoft AD login successful!")
    except Exception:
        logger.exception("Failure while attempting AD login")
    finally:
        if executor:
            executor.quit()


def microsoft_login(executor: SeleniumExecutor):
    # Read secrets
    logger.info("Reading secrets from environment")
    email = os.environ.get("EMAIL")
    password = os.environ.get("PASSWORD")
    totp_secret = os.environ.get("TOTP_SECRET")

    executor.wait_for_element(
        By.NAME,
        "loginfmt",
    ).enter_text(
        By.NAME,
        "loginfmt",
        email,
    ).click(
        By.CLASS_NAME,
        "button_primary",
        log="Entered email",
    ).wait_for_element(
        By.XPATH,
        '//*[contains(text(),"Enter password")]',
    ).enter_text(
        By.NAME,
        "passwd",
        password,
    ).click(
        By.CLASS_NAME,
        "button_primary",
        log="Entered password",
    ).wait_for_element(By.ID, "signInAnotherWay").click(
        By.ID,
        "signInAnotherWay",
        log="Requested alternate sign-in",
    ).wait_for_element(
        By.XPATH,
        '//*[@data-value="PhoneAppOTP"]',
    ).click(
        By.XPATH,
        '//*[@data-value="PhoneAppOTP"]',
        log="Selected TOTP sign-in method",
    ).wait_for_element(
        By.XPATH,
        '//*[contains(text(),"Enter code")]',
    ).enter_text(
        By.NAME,
        "otc",
        TOTP(totp_secret).now(),
    ).click(
        By.NAME,
        "rememberMFA",
    ).click(
        By.CLASS_NAME,
        "button_primary",
        log="Entered TOTP",
    ).wait_for_element(
        By.XPATH,
        '//*[contains(text(),"Stay signed in?")]',
    ).click(
        By.CLASS_NAME,
        "button_primary",
    )

    return executor


def login():
    logger.info(
        f"Beginning automated SSO login for AWS SSO session <{AWS_SSO_SESSION}>"
    )

    # Check token expiry timestamp
    token_expiry_timestamp = get_token_expiry()

    if token_expiry_timestamp - datetime.now(UTC) > TOKEN_EXPIRY_THRESHOLD:
        logger.info("Access token is still valid, skipping login")
        return

    if token_expiry_timestamp < datetime.now(UTC):
        logger.warning("Access token has expired, logging in again")
    else:
        logger.warning("Access token is about to expire, logging in again")

    logger.info("Checking if user is already logged in")
    process = subprocess.Popen(
        [
            AWS_BINARY,
            "sso",
            "login",
            "--sso-session",
            AWS_SSO_SESSION,
            "--no-browser",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdoutlines = []

    url = None
    while True:
        raw_line = process.stdout.readline()
        stdoutlines.append(raw_line)

        if not raw_line:
            raise Exception("AWS SSO login command failed")

        line = raw_line.decode().strip()
        if re.match(r".*user_code=", line):
            url = line
            break

    # Get a firefox driver
    executor = get_executor()

    # Open the login page
    executor.open(url)

    # Execute login
    try:
        microsoft_login(executor)

        executor.wait_for_element(
            By.ID,
            "user-code",
        ).click(
            By.ID,
            "cli_verification_btn",
            log="Confirmed code",
        ).wait_for_element(
            By.XPATH,
            '//*[@data-testid="allow-access-button"]',
        ).click(
            By.XPATH,
            '//*[@data-testid="allow-access-button"]',
            log="Allowed AWS OAuth",
        )

        logger.info("Login successful")
    except Exception:
        logger.exception("Failure while attempting SSO login")

        # Terminate the AWS process, in case it is still running
        process.terminate()
    finally:
        executor.quit()


if __name__ == "__main__":
    mode = "aws-login" if len(sys.argv) < 2 else sys.argv[1]

    if mode == "totp":
        print(TOTP(os.environ.get("TOTP_SECRET")).now())
        sys.exit()

    elif mode == "aws-login":
        login()

    elif mode == "ad-check":
        microsoft_active_directory_check()

    function_profiler.write_csv("profiled.csv")

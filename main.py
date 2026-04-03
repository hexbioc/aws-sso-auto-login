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

# TODO: Add proper config validation
AWS_BINARY = os.getenv("AWS_BINARY", "")
AWS_STS_PROFILE = os.getenv("AWS_STS_PROFILE", "")
AWS_SSO_SESSION = os.getenv("AWS_SSO_SESSION", "")

AD_CHECK_URL = os.getenv("AD_CHECK_URL", "https://google.com")
FIREFOX_BINARY_PATH = os.getenv("FIREFOX_BINARY_PATH")

AWS_SSO_CACHE_PATH = os.path.expanduser("~/.aws/sso/cache")
TOKEN_EXPIRY_THRESHOLD = timedelta(minutes=10)

AD_URL_PREFIX = "https://login.microsoftonline.com"

SSO_CHECK_TIMEOUT_SECONDS = 10

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
    executor = SeleniumExecutor(headless=headless, driver_path=FIREFOX_BINARY_PATH)

    return executor


def microsoft_active_directory_check():
    logger.info("Checking if Microsoft AD login is required")

    executor = None

    try:
        executor = get_executor()
        executor.open(AD_CHECK_URL)

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
    email = os.environ.get("EMAIL", "")
    password = os.environ.get("PASSWORD", "")
    totp_secret = os.environ.get("TOTP_SECRET", "")

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
    )

    # Sometimes, the app OTP can fail, so we check for both elements
    # Target is to click on the TOTP option
    signin_another_way_opt = (By.ID, "signInAnotherWay")
    totp_opt = (By.XPATH, '//*[@data-value="PhoneAppOTP"]')
    
    executor.wait_for_any_of([signin_another_way_opt, totp_opt])

    if executor.element_exists(*signin_another_way_opt):
        executor.click(
            *signin_another_way_opt,
            log="Requested alternate sign-in",
        ).wait_for_element(
            *totp_opt,
        )

    executor.click(
        *totp_opt,
        log="Selected TOTP sign-in method",
    ).wait_for_element(
        By.XPATH,
        '//*[contains(text(),"Enter code")]',
    ).enter_text(
        By.NAME,
        "otc",
        TOTP(totp_secret).now(),
    ).click(
        By.CLASS_NAME,
        "button_primary",
        log="Entered TOTP",
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
    start_time = time.time()
    while True:
        raw_line = process.stdout.readline() # pyright: ignore[reportOptionalMemberAccess]
        stdoutlines.append(raw_line)

        if not raw_line:
            raise Exception("AWS SSO login command failed")

        line = raw_line.decode().strip()
        if re.match(r"^https://oidc\.[^\.]+\.amazonaws\.com/authorize", line):
            url = line
            break

        if (time.time() - start_time) > SSO_CHECK_TIMEOUT_SECONDS:
            raise Exception('AWS SSO login command timed-out')

    # Get a firefox driver
    executor = get_executor()

    # Open the login page
    executor.open(url)

    # Execute login
    try:
        microsoft_login(executor)

        # We either get a success message, or a button to allow access
        success_message_sel = (By.ID, 'success-message')
        allow_btn_sel = (By.XPATH, '//*[@data-testid="allow-access-button"]')

        executor.wait_for_any_of([success_message_sel, allow_btn_sel])

        if executor.element_exists(*allow_btn_sel):
            executor.click(
                *allow_btn_sel,
                log="Allowed AWS OAuth",
            )

        logger.info("SSO login successful")
    except Exception:
        logger.exception("Failure while attempting SSO login")
    finally:
        # Release browser resources
        executor.quit()

        # Terminate the AWS process, in case it is still running
        process.terminate()


if __name__ == "__main__":
    mode = "aws-login" if len(sys.argv) < 2 else sys.argv[1]

    if mode == "totp":
        print(TOTP(os.environ.get("TOTP_SECRET", "")).now())
        sys.exit()

    elif mode == "aws-login":
        login()

    elif mode == "ad-check":
        microsoft_active_directory_check()

    function_profiler.write_csv("profiled.csv")

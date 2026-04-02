import time

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from logger import logger
from profiler import function_profiler


EXPLICIT_WAIT_SECONDS = 30
INTERACTION_DELAY_SECONDS = 0.5


class SeleniumExecutor:
    def __init__(
        self,
        *,
        headless=True,
        explicit_wait_seconds=EXPLICIT_WAIT_SECONDS,
        interaction_delay_seconds=INTERACTION_DELAY_SECONDS,
    ):
        options = Options()
        if headless:
            options.add_argument("--headless")

        self.driver = webdriver.Firefox(options=options)
        self.explicit_wait_seconds = explicit_wait_seconds
        self.interaction_delay_seconds = interaction_delay_seconds

    @function_profiler.profile
    def open(self, url: str):
        self.driver.get(url)

        return self

    @function_profiler.profile
    def wait_for_element(self, by: str, selector: str):
        try:
            WebDriverWait(self.driver, self.explicit_wait_seconds).until(
                EC.presence_of_element_located((by, selector))
            )
        except Exception:
            logger.exception(
                f"Exception while waiting for element selector <{selector}> by <{by}>"
            )
        time.sleep(self.interaction_delay_seconds)

        return self

    @function_profiler.profile
    def click(
        self,
        by: str,
        selector: str,
        *,
        log: str | None = None,
    ):
        # Click element
        self.driver.find_element(by, selector).click()

        if log is not None:
            logger.info(log)

        return self

    @function_profiler.profile
    def enter_text(
        self,
        by: str,
        selector: str,
        text: str,
        *,
        log: str | None = None,
    ):
        self.driver.find_element(by, selector).send_keys(text)

        if log is not None:
            logger.info(log)

        return self

    @function_profiler.profile
    def quit(self, quit_delay_seconds: float = INTERACTION_DELAY_SECONDS):
        time.sleep(quit_delay_seconds)
        self.driver.quit()

        return None

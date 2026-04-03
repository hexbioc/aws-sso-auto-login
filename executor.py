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
        driver_path=None,
        explicit_wait_seconds=EXPLICIT_WAIT_SECONDS,
        interaction_delay_seconds=INTERACTION_DELAY_SECONDS,
    ):
        options = Options()
        if headless:
            options.add_argument("--headless")

        if driver_path:
            options.binary_location = driver_path

        self.driver = webdriver.Firefox(options=options)
        self.explicit_wait_seconds = explicit_wait_seconds
        self.interaction_delay_seconds = interaction_delay_seconds

    @function_profiler.profile
    def open(self, url: str):
        self.driver.get(url)

        return self
    
    @function_profiler.profile
    def element_exists(self, by: str, selector: str):
        try:
            self.driver.find_element(by, selector)
            return True
        except:
            return False
    
    @function_profiler.profile
    def wait_for_any_of(self, selectors: list[tuple[str, str]]):
        try:
            WebDriverWait(self.driver, self.explicit_wait_seconds).until(
                EC.any_of(*[
                    EC.presence_of_element_located(sel)
                    for sel in selectors
                ])
            )
        except Exception:
            logger.exception(
                f"Exception while waiting any of selectors <{selectors}>"
            )
            raise

        time.sleep(self.interaction_delay_seconds)

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
            raise

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
        WebDriverWait(self.driver, self.explicit_wait_seconds).until(
            EC.element_to_be_clickable((by, selector)),
        ).click()

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
        WebDriverWait(self.driver, self.explicit_wait_seconds).until(
            EC.element_to_be_clickable((by, selector)),
        ).send_keys(text)

        if log is not None:
            logger.info(log)

        return self

    @function_profiler.profile
    def quit(self, quit_delay_seconds: float = INTERACTION_DELAY_SECONDS):
        time.sleep(quit_delay_seconds)
        self.driver.quit()

        return None

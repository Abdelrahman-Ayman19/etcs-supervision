from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class WebFormPage:
    URL = "https://www.selenium.dev/selenium/web/web-form.html"
    TEXT_INPUT = (By.NAME, "my-text")
    SUBMIT = (By.CSS_SELECTOR, "button")
    MESSAGE = (By.ID, "message")

    def __init__(self, driver, timeout=10):  # initialize the driver and the wait
        self.driver = driver
        self.wait = WebDriverWait(driver, timeout)
    
    def open(self):  # opens the class's URL
        self.driver.get(self.URL)  
        return self

    def fill_text(self, value):
        self.wait.until(EC.visibility_of_element_located(self.TEXT_INPUT)).send_keys(value)
        return self
    
    def submit(self):
        self.wait.until(EC.element_to_be_clickable(self.SUBMIT)).click()
        return self
    
    def message_text(self):
        return self.wait.until(EC.visibility_of_element_located(self.MESSAGE)).text
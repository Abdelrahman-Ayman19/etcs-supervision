import unittest
from web_form_page import WebFormPage
import os
from selenium import webdriver

class TestWebForm(unittest.TestCase):
    def setUp(self):
        options = webdriver.ChromeOptions()
        if os.environ.get("HEADLESS", "1") == "1":
            options.add_argument("--headless=new")
        self.driver = webdriver.Chrome(options=options)
        self.page = WebFormPage(self.driver)
        self.driver.maximize_window()

    def tearDown(self):  # counter to setUp!! runs after every test case
        self.driver.quit()

    def test_submitting_text_shows_confirmation(self):
        self.page.open().fill_text("selenium").submit()
        self.assertEqual(self.page.message_text(), "Received!")
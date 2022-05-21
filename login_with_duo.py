import os  
import sys
import time
from selenium import webdriver  
from selenium.webdriver.common.keys import Keys  
from selenium.webdriver.chrome.options import Options 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

try:
    from duo_gen import generate_next_token
    login_manually = False
    print("Automatic Login")
except ModuleNotFoundError:
    login_manually = True
    print("Manual Login")

class AnyEC:
    """ Use with WebDriverWait to combine expected_conditions
        in an OR.
    """
    def __init__(self, *args):
        self.ecs = args
    def __call__(self, driver):
        for i, fn in enumerate(self.ecs):
            try:
                result = fn(driver)
                if result:
                    return i, result
            except:
                pass
        return False
    
def login_to_canvas(driver, page, wait_until):
    wait = WebDriverWait(driver, 10)
    driver.get(page)
    
    if driver.current_url == page:
        return
        
    wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "MIT Students, Faculty, and Staff"))).click()
    
    if login_manually:
        print("Login and press enter to continue")
        input()
    else:
        # Click login by certificate button when it appears
        wait.until(EC.element_to_be_clickable((By.NAME, "login_certificate"))).click()

        # Jump into iframe for entering passcode
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, 'duo_iframe')))
        wait.until(EC.element_to_be_clickable((By.ID, "passcode")))

        # Choose passcode duo authentication method
        passcode_button = driver.find_element_by_id("passcode")
        passcode_button.click()

        # Get passcode input
        passcode_input = driver.find_element_by_name("passcode")

        # Generate next passcode and input it
        next_password = generate_next_token()
        passcode_input.send_keys(next_password)

        # Submit the passcode to duo
        passcode_button.click()
    
    # Wait until logged in
    wait.until(wait_until)

def login_to_lms(driver, page, wait_until):
    wait = WebDriverWait(driver, 10)
    driver.get(page)
    time.sleep(3)
    
    wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "learning-header")))
    
    i, result = wait.until(AnyEC(EC.element_to_be_clickable((By.LINK_TEXT, "Sign in")), \
                                 EC.visibility_of_element_located((By.CLASS_NAME, "user-dropdown"))))
    if i == 0:
        result.click()
    else:
        return 
    
    wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "button-saml-mit-kerberos"))).click()
    
    try:
        driver.find_element(by=By.CLASS_NAME, value="user-dropdown")
        return
    except:
        pass
    
    if login_manually:
        print("Login and press enter to continue")
        input()
    else:
        # Click login by certificate button when it appears
        wait.until(EC.element_to_be_clickable((By.NAME, "login_certificate"))).click()

        # Jump into iframe for entering passcode
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, 'duo_iframe')))
        wait.until(EC.element_to_be_clickable((By.ID, "passcode")))

        # Choose passcode duo authentication method
        passcode_button = driver.find_element_by_id("passcode")
        passcode_button.click()

        # Get passcode input
        passcode_input = driver.find_element_by_name("passcode")

        # Generate next passcode and input it
        next_password = generate_next_token()
        passcode_input.send_keys(next_password)

        # Submit the passcode to duo
        passcode_button.click()
    
    # Wait until logged in
    wait.until(wait_until)

import os  
import sys
import json
import time
import shutil
from selenium import webdriver  
from selenium.webdriver.common.keys import Keys  
from selenium.webdriver.chrome.options import Options 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from login_with_duo import login_to_canvas, login_to_lms
from selenium.common.exceptions import TimeoutException

SCRIPT_LOCATION = os.path.abspath('')
DATA_FOLDER = os.path.join(SCRIPT_LOCATION, 'data/')
COURSES_URL = "https://canvas.mit.edu/courses"

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

def get_module_type(module):
    module_class = module.get_attribute("class").split()

    if "context_external_tool" in module_class:
        return "external_tool"
    elif "assignment" in module_class:
        return "assignment"
    elif "wiki_page" in module_class:
        return "wiki"
    elif "attachment" in module_class:
        return "attachment"
    elif "external_url" in module_class:
        return "external_url"
    elif "quiz" in module_class:
        return "quiz"
    
def wait_for_downloads():
    not_all_downloaded = True
    while not_all_downloaded:
        not_all_downloaded = any(f.endswith("crdownload") for f in os.listdir(DATA_FOLDER))
        time.sleep(1)
            
def load_page_and_wait(driver, page, wait_condition=None, fail_condition=None):
    driver.get(page)
    if wait_condition is not None:
        condition = wait_condition
        if fail_condition is not None:
            condition = AnyEC(wait_condition, fail_condition)
        try:
            result = wait.until(condition)
            if fail_condition is not None:
                if result[0] == 1:
                    return False
                else:
                    return result[1]
            else:
                return result
        except TimeoutException:
            if driver.current_url != page:
                load_page_and_wait(driver, page, wait_condition, fail_condition)
            else:
                raise RuntimeError("Page did not meet expected condition")
    else:
        if fail_condition is not None:
            if driver.current_url != page:
                try:
                    wait.until(fail_condition)
                    return False
                except TimeoutException:
                    load_page_and_wait(driver, page, wait_condition, fail_condition)
            else:
                raise RuntimeError("Did not navigate to page")
        else:
            if driver.current_url != page:
                load_page_and_wait(driver, page, wait_condition)
            else:
                raise RuntimeError("Did not navigate to page")

        
if __name__ == "__main__":
    if os.path.exists(DATA_FOLDER):
        shutil.rmtree(DATA_FOLDER)
    os.mkdir(DATA_FOLDER)
    
    print_settings = {
        "recentDestinations": [{
            "id": "Save as PDF",
            "origin": "local",
            "account": ""
        }],
        "selectedDestinationId": "Save as PDF",
        "version": 2
    }
    
    chrome_options = Options()  
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--ignore-urlfetcher-cert-requests")
    chrome_options.add_argument("--enable-print-browser")
    chrome_options.add_argument("--kiosk-printing")
    chrome_options.add_experimental_option("prefs", {
        "plugins.always_open_pdf_externally": True,
        "download.default_directory" : DATA_FOLDER,
        "savefile.default_directory": DATA_FOLDER,
        "profile.managed_auto_select_certificate_for_urls": ['{"pattern":"https://idp.mit.edu:446","filter":{"ISSUER":{"OU":"Client CA v1"}}}'],
        "printing.print_preview_sticky_settings.appState": json.dumps(print_settings)
        })  

    driver = webdriver.Chrome(options=chrome_options) 
    wait = WebDriverWait(driver, 10)
    
    login_to_canvas(driver, COURSES_URL, EC.visibility_of_element_located((By.ID, "my_courses_table")))
    
    current_course_table = driver.find_element(by=By.ID, value="my_courses_table")
    current_course_links = current_course_table.find_elements(by=By.TAG_NAME, value="a")
    past_course_table = driver.find_element(by=By.ID, value="past_enrollments_table")
    past_course_links = past_course_table.find_elements(by=By.TAG_NAME, value="a")
    course_links = current_course_links + past_course_links
    course_urls_names = [(el.get_attribute("href"), \
                        el.get_attribute("innerText").replace(" ", "_").replace(".", "_")) \
                        for el in course_links]
    
    page_not_available = EC.visibility_of_element_located((By.CSS_SELECTOR, "#flash_message_holder > *"))
    
    for course_url, course_name in course_urls_names:
        os.mkdir(os.path.join(DATA_FOLDER, course_name))
    
        # Modules        
        if load_page_and_wait(driver, course_url + "/modules", \
                              EC.visibility_of_element_located((By.ID, "context_modules")), page_not_available):
            modules = driver.find_elements(by=By.CLASS_NAME, value="context_module_item")
            module_url_types = []
            for module in modules:
                if module.get_attribute("id") != "context_module_item_blank":
                    try:
                        url = module.find_element(by=By.TAG_NAME, value="a").get_attribute("href")
                        module_url_types.append((url, get_module_type(module)))
                    except:
                        pass

            downloaded_files = set()

            for module_url, module_type in module_url_types:
                print(module_url)
                if module_type == "wiki":
                    load_page_and_wait(driver, module_url, EC.visibility_of_element_located((By.ID, "wiki_page_show")))

                    try:
                        driver.find_element(by=By.ID, value="tool_content")
                        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "tool_content")))
                        driver.switch_to.default_content()
                    except:
                        pass

                    file_downloads = driver.find_elements(by=By.CLASS_NAME, value="file_download_btn")
                    for file_btn in file_downloads:
                        file_url = file_btn.get_attribute("href")
                        file_url = file_url[:file_url.rindex("/")].split("/")[-1]

                        if file_url not in downloaded_files:
                            downloaded_files.add(file_url)
                            time.sleep(1)
                            file_btn.click()

                    driver.execute_script('window.print();')
                elif module_type == "attachment":
                    load_page_and_wait(driver, module_url, EC.visibility_of_element_located((By.PARTIAL_LINK_TEXT, "Download")))

                    download_link = driver.find_element(by=By.PARTIAL_LINK_TEXT, value="Download")

                    file_url = download_link.get_attribute("href")
                    file_url = file_url[:file_url.rindex("/")].split("/")[-1]

                    if file_url not in downloaded_files:
                        downloaded_files.add(file_url)
                        download_link.click()

                elif module_type == "assignment":
                    load_page_and_wait(driver, module_url, EC.visibility_of_element_located((By.ID, "assignment_show")))

                    try:
                        driver.find_element(by=By.ID, value="tool_content")
                        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "tool_content")))
                        driver.switch_to.default_content()
                    except:
                        pass

                    file_downloads = driver.find_elements(by=By.CLASS_NAME, value="file_download_btn")
                    for file_btn in file_downloads:
                        file_url = file_btn.get_attribute("href")
                        file_url = file_url[:file_url.rindex("/")].split("/")[-1]

                        if file_url not in downloaded_files:
                            downloaded_files.add(file_url)
                            time.sleep(1)
                            file_btn.click()

                    driver.execute_script('window.print();')
                elif module_type == "external_tool":
                    load_page_and_wait(driver, module_url, EC.frame_to_be_available_and_switch_to_it((By.ID, "tool_content")))
                    driver.execute_script('window.print();')
                elif module_type == "external_url":
                    i, external_button = load_page_and_wait(driver, module_url, \
                                                         AnyEC(EC.visibility_of_element_located((By.ID, "open_url_button")), \
                                                              EC.visibility_of_element_located((By.CSS_SELECTOR, "a.external"))))
                                    
                    external_url = external_button.get_attribute("href")

                    if i == 0:
                        driver.switch_to.window(driver.window_handles[1])
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])

                    if external_url.startswith("https://lms.mitx.mit.edu"):
                        login_to_lms(driver, external_url, EC.visibility_of_element_located((By.CLASS_NAME, "learning-header")))
                    else:
                        driver.get(external_url)
                    time.sleep(3)

                    driver.execute_script('window.print();')
                elif module_type == "quiz":
                    load_page_and_wait(driver, module_url, EC.visibility_of_element_located((By.ID, "content")))

                    try:
                        driver.find_element(by=By.ID, value="tool_content")
                        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "tool_content")))
                        driver.switch_to.default_content()
                    except:
                        pass

                    file_downloads = driver.find_elements(by=By.CLASS_NAME, value="file_download_btn")
                    for file_btn in file_downloads:
                        file_url = file_btn.get_attribute("href")
                        file_url = file_url[:file_url.rindex("/")].split("/")[-1]

                        if file_url not in downloaded_files:
                            downloaded_files.add(file_url)
                            time.sleep(1)
                            file_btn.click()

                    driver.execute_script('window.print();')
                else:
                    raise ValueError("unknown module type")
                time.sleep(1)


            wait_for_downloads()

            os.mkdir(os.path.join(DATA_FOLDER, course_name, "modules"))
            for f in os.listdir(DATA_FOLDER):
                if os.path.isfile(os.path.join(DATA_FOLDER, f)):
                    shutil.move(os.path.join(DATA_FOLDER, f), \
                                os.path.join(DATA_FOLDER, course_name, "modules", f))

        # Announcements
        if load_page_and_wait(driver, course_url + "/announcements", \
                              EC.visibility_of_element_located((By.CLASS_NAME, "announcements-v2__wrapper")), \
                              page_not_available):
            announcement_rows = driver.find_elements(by=By.CLASS_NAME, value="ic-announcement-row")
            announcement_links = [row.find_element(by=By.TAG_NAME, value="a") for row in announcement_rows]
            announcement_urls = [link.get_attribute("href") for link in announcement_links]

            for announcement_url in announcement_urls:
                print(announcement_url)
                load_page_and_wait(driver, announcement_url, EC.visibility_of_element_located((By.ID, "discussion_topic")))
                driver.execute_script('window.print();')
                time.sleep(1)

            os.mkdir(os.path.join(DATA_FOLDER, course_name, "announcements"))
            for f in os.listdir(DATA_FOLDER):
                if os.path.isfile(os.path.join(DATA_FOLDER, f)):
                    shutil.move(os.path.join(DATA_FOLDER, f), \
                                os.path.join(DATA_FOLDER, course_name, "announcements", f))


        # Syllabus
        if load_page_and_wait(driver, course_url + "/assignments/syllabus", \
                  EC.visibility_of_element_located((By.ID, "course_syllabus")), \
                  page_not_available):

            file_downloads = driver.find_elements(by=By.CLASS_NAME, value="file_download_btn")
            for file_btn in file_downloads:
                file_url = file_btn.get_attribute("href")
                file_url = file_url[:file_url.rindex("/")]

                if file_url not in downloaded_files:
                    downloaded_files.add(file_url)
                    time.sleep(1)
                    file_btn.click()

            driver.execute_script('window.print();')
            
            wait_for_downloads()

            os.mkdir(os.path.join(DATA_FOLDER, course_name, "syllabus"))
            for f in os.listdir(DATA_FOLDER):
                if os.path.isfile(os.path.join(DATA_FOLDER, f)):
                    shutil.move(os.path.join(DATA_FOLDER, f), \
                                os.path.join(DATA_FOLDER, course_name, "syllabus", f))

        # Files
        folder_prefix = course_url + "/files/folder/"
        
        def collect_files(url):
            if load_page_and_wait(driver, url, \
                                  EC.visibility_of_element_located((By.CLASS_NAME, "ef-directory-header")), \
                                  page_not_available):

                files_and_folder_links = driver.find_elements(by=By.CLASS_NAME, value="ef-name-col__link")
                files_and_folder_urls = [link.get_attribute("href") for link in files_and_folder_links]

                folder_urls = []
                for sub_url in files_and_folder_urls:
                    if sub_url.startswith(folder_prefix):
                        folder_urls.append(sub_url)
                    else:
                        stripped_url = sub_url[:sub_url.rindex("/")].split("/")[-1]
                        if stripped_url not in downloaded_files:
                            driver.get(sub_url)
                            downloaded_files.add(stripped_url)
                            time.sleep(1)

                for folder_url in folder_urls:
                    collect_files(folder_url)
                
        collect_files(course_url + "/files")
        
        wait_for_downloads()
            
        os.mkdir(os.path.join(DATA_FOLDER, course_name, "other_files"))
        for f in os.listdir(DATA_FOLDER):
            if os.path.isfile(os.path.join(DATA_FOLDER, f)):
                shutil.move(os.path.join(DATA_FOLDER, f), \
                            os.path.join(DATA_FOLDER, course_name, "other_files", f))

        
        # Assignments
        if load_page_and_wait(driver, course_url + "/assignments", \
                              AnyEC(EC.visibility_of_element_located((By.ID, "assignment_group_upcoming")), \
                                    EC.visibility_of_element_located((By.ID, "assignment_group_past")), \
                                    EC.visibility_of_element_located((By.ID, "assignment_group_undated")), \
                                    EC.visibility_of_element_located((By.ID, "assignment_group_overdue_assignments"))), \
                              page_not_available):
            assignments = driver.find_elements(by=By.CLASS_NAME, value="assignment")
            assignment_urls = [assignment.find_element(by=By.TAG_NAME, value="a").get_attribute("href") \
                               for assignment in assignments]

            for assignment_url in assignment_urls:
                print(assignment_url)
                load_page_and_wait(driver, assignment_url, EC.visibility_of_element_located((By.ID, "content")))
                
                try:
                    driver.find_element(by=By.ID, value="tool_content")
                    wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "tool_content")))
                    driver.switch_to.default_content()
                except:
                    pass

                file_downloads = driver.find_elements(by=By.CLASS_NAME, value="file_download_btn")
                for file_btn in file_downloads:
                    file_url = file_btn.get_attribute("href")
                    file_url = file_url[:file_url.rindex("/")]

                    downloaded_files.add(file_url)
                    time.sleep(1)
                    file_btn.click()

                driver.execute_script('window.print();')
                
        wait_for_downloads()
            
        os.mkdir(os.path.join(DATA_FOLDER, course_name, "assignments"))
        for f in os.listdir(DATA_FOLDER):
            if os.path.isfile(os.path.join(DATA_FOLDER, f)):
                shutil.move(os.path.join(DATA_FOLDER, f), \
                            os.path.join(DATA_FOLDER, course_name, "assignments", f))

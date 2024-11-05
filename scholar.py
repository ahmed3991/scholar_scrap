import pandas as pd
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import os
import tempfile

# Base download directory
download_dir = os.path.abspath("./pdfs")
if not os.path.exists(download_dir):
    os.makedirs(download_dir)

# Temporary directory for user data to avoid session cleanup issues
temp_user_data_dir = tempfile.mkdtemp()

class ChromeDriverManager:
    """Context manager for ChromeDriver to ensure proper initialization and teardown."""

    def __init__(self, download_path=None):
        self.download_path = download_path
        self.driver = None

    def __enter__(self):
        self.driver = get_chrome_driver(self.download_path)
        return self.driver

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            self.driver.quit()

def get_chrome_driver(download_path=None):
    """Create a new instance of undetected Chrome with specified options."""
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={temp_user_data_dir}")  # Use a temporary profile
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Set download preferences if a download path is provided
    if download_path:
        prefs = {
            "download.default_directory": download_path,
            "download.prompt_for_download": False,  # Prevents download prompt
            "plugins.always_open_pdf_externally": True  # Forces PDFs to download instead of opening in the viewer
        }
        options.add_experimental_option("prefs", prefs)

    # Start the Chrome driver
    driver = uc.Chrome(options=options)

    # Use CDP command to force download behavior
    if download_path:
        driver.execute_cdp_cmd(
            "Page.setDownloadBehavior",
            {"behavior": "allow", "downloadPath": download_path}
        )

    return driver

def wait_and_click_verification_element(driver, by, value, timeout=4):
    """Waits for a specific element, typically a verification or CAPTCHA element, to appear and clicks it."""
    try:
        # Wait for the element to appear and be clickable (e.g., reCAPTCHA checkbox)
        verification_element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        print("Verification element found. Waiting 3 seconds before clicking.")
        time.sleep(2)  # Wait 3 seconds before clicking for the element to stabilize
        verification_element.click()
        print("Clicked verification element. Waiting an additional 10 seconds for processing.")
        time.sleep(5)  # Wait 10 seconds after clicking for any follow-up processing
    except Exception as e:
        print(f"Verification element not found or could not be clicked: {e}")

def is_pdf_downloaded(author_dir):
    """Check if a PDF file has been downloaded to the specified directory."""
    for file_name in os.listdir(author_dir):
        if file_name.endswith(".pdf"):
            return True
    return False

def search_user_profile(driver, user_name):
    """Searches Google Scholar for a user and navigates to their profile."""
    driver.get("https://scholar.google.com/")
    time.sleep(random.uniform(2, 4))

    # Perform a search
    search_box = driver.find_element(By.NAME, "q")
    search_box.send_keys(user_name)
    search_box.submit()
    time.sleep(random.uniform(2, 4))

    # Attempt to access profile with adaptive wait
    for attempt in range(5):
        try:
            profile_link = driver.find_element(By.CSS_SELECTOR, "h4.gs_rt2 a")
            profile_link.click()
            print(f"Navigated to profile for user: {user_name}")
            return
        except Exception:
            print(f"Attempt {attempt + 1}: Verification detected. Attempting to handle verification.")
            wait_and_click_verification_element(driver, By.ID, "recaptcha-anchor", timeout=1)  # Adjust selector as needed

def extract_pdf_links(driver):
    """Extracts PDF links from the user's profile and returns them as a list."""
    article_links = driver.find_elements(By.CSS_SELECTOR, ".gsc_a_at")
    pdf_links = []

    scrapped = 0

    for article in article_links:
        if scrapped >= 10:  # Stop after scraping 10 articles
            break

        article.click()
        time.sleep(random.uniform(2, 4))

        # Look for all anchor tags with potential PDF links
        anchors = driver.find_elements(By.TAG_NAME, "a")
        found_pdf = False

        for anchor in anchors:
            href = anchor.get_attribute("href")
            if href and (".pdf" in href or "viewFile" in href):
                pdf_links.append(href)
                print(f"Found PDF link: {href}")
                found_pdf = True
                break

        if not found_pdf:
            print("No PDF link found on this page.")
        else:
            scrapped += 1

        driver.back()
        time.sleep(random.uniform(2, 3))

    return pdf_links

def download_pdfs_with_selenium(pdf_links, author_dir):
    """Downloads PDFs from extracted links, with retries and manual verification."""
    author_dir = os.path.join(download_dir, author_dir)
    if not os.path.exists(author_dir):
        os.makedirs(author_dir)

    for i, pdf_url in enumerate(pdf_links, start=1):
        success = False
        with ChromeDriverManager(download_path=author_dir) as driver:
            for attempt in range(5):
                try:
                    print(f"Attempting to download PDF {i} at {pdf_url} (Attempt {attempt + 1})")
                    driver.get(pdf_url)
                    time.sleep(random.uniform(3, 5))  # Allow time for download to start

                    if is_pdf_downloaded(author_dir):
                        print(f"Download successful for: {pdf_url}")
                        success = True
                        break
                    else:
                        print("No PDF file detected, retrying...")

                    time.sleep(5)
                except Exception as e:
                    print(f"Error during download attempt {attempt + 1} for {pdf_url}: {e}")

                if attempt == 4 and not success:
                    print(f"Manual verification required for: {pdf_url}")
                    wait_and_click_verification_element(driver, By.ID, "recaptcha-anchor", timeout=120)

def download_pdfs_for_user(researcher_name: str, scopus_id: str) -> None:
    user_name = researcher_name

    author_dir = os.path.join(download_dir, scopus_id)
    if os.path.exists(author_dir):
        return

    with ChromeDriverManager() as driver:
        search_user_profile(driver, user_name)
        pdf_links = extract_pdf_links(driver)

    print("List of PDF links:")
    for link in pdf_links:
        print(link)

    download_pdfs_with_selenium(pdf_links, scopus_id)

if __name__ == "__main__":
    file = pd.read_csv('data/cleaned_authors_non_eloued.csv', delimiter=',')
    authors = file.values.tolist()

    for author in authors:
        try:
            download_pdfs_for_user(str(author[1]).strip(), str(author[0]).strip())
        except Exception as e:
            print(f"An error occurred for author {author[1]}: {e}")

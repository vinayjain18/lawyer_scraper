"""
Trivandrum Bar Association Lawyer Data Scraper with Pagination

This script addresses both the modal issues and implements pagination handling
to scrape all lawyers from the Trivandrum Bar Association website.
"""

import re
import time
import csv
import os
import random
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    StaleElementReferenceException,
    ElementClickInterceptedException,
    WebDriverException
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("pagination_scraper.log"),
        logging.StreamHandler()
    ],
    encoding="utf-8"
)
logger = logging.getLogger(__name__)

# Constants
BASE_URL = "https://thetrivandrumbarassociation.com/Member"
CSV_FILE = "lawyers_data_complete.csv"
MAX_RETRIES = 3
PAGE_LOAD_WAIT = 10  # Wait time for page load in seconds

class PaginationScraper:
    def __init__(self):
        self.driver = None
        self.total_lawyers_scraped = 0
        self.current_page = 1
        self.max_pages = 915
    
    def setup_driver(self):
        """Set up the WebDriver with appropriate options."""
        logger.info("Setting up the WebDriver...")
        
        chrome_options = Options()
        # Uncomment for headless mode if needed
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        try:
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )
            self.driver.set_page_load_timeout(30)
            self.driver.maximize_window()
            logger.info("WebDriver setup complete.")
            return True
        except Exception as e:
            logger.error(f"Failed to setup WebDriver: {e}")
            return False
    
    def create_csv_file(self):
        """Create a CSV file with headers if it doesn't exist."""
        if not os.path.exists(CSV_FILE):
            with open(CSV_FILE, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow([
                    'Name', 
                    'Mobile Number', 
                    'Email', 
                    'Enrollment Number', 
                    'Office Address', 
                    'Residence Address',
                    'Page Number'  # Added page number for tracking
                ])
            logger.info(f"Created CSV file: {CSV_FILE}")
    
    def save_to_csv(self, lawyer_data):
        """Save lawyer data to CSV file."""
        try:
            with open(CSV_FILE, 'a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                # Log the actual data being saved
                save_data = {
                    'Name': lawyer_data.get('Name', ''),
                    'Mobile Number': lawyer_data.get('Mobile Number', ''),
                    'Email': lawyer_data.get('Email', ''),
                    'Enrollment Number': lawyer_data.get('Enrollment Number', ''),
                    'Office Address': lawyer_data.get('Office Address', ''),
                    'Residence Address': lawyer_data.get('Residence Address', ''),
                    'Page Number': self.current_page  # Add the current page number
                }
                logger.info(f"Saving to CSV: {save_data}")
                
                writer.writerow([
                    save_data['Name'],
                    save_data['Mobile Number'],
                    save_data['Email'],
                    save_data['Enrollment Number'],
                    save_data['Office Address'],
                    save_data['Residence Address'],
                    save_data['Page Number']
                ])
                return True
        except Exception as e:
            logger.error(f"Error saving data to CSV: {e}")
            return False
    
    def close_all_modals(self):
        """Close all open modals by clicking their close buttons or pressing ESC."""
        try:
            # First try to find and click any close buttons
            close_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button.btn-close, button.close, .modal .close")
            if close_buttons:
                for button in close_buttons:
                    try:
                        button.click()
                        time.sleep(0.5)  # Short delay to let modal close
                    except:
                        pass
            
            # If there are still modals, try pressing ESC key
            modals = self.driver.find_elements(By.CSS_SELECTOR, ".modal.show")
            if modals:
                actions = ActionChains(self.driver)
                actions.send_keys(Keys.ESCAPE).perform()
                time.sleep(0.5)
            
            # Last resort - reload the page
            modals = self.driver.find_elements(By.CSS_SELECTOR, ".modal.show")
            if modals:
                logger.warning("Modals still present after attempts to close. Reloading page.")
                self.driver.refresh()
                time.sleep(2)
            
            return True
        except Exception as e:
            logger.error(f"Error closing modals: {e}")
            return False
    
    def extract_from_card(self, card):
        """Extract basic information directly from the card."""
        card_data = {}
        
        try:
            # Try to get name
            try:
                name_elem = card.find_element(By.CSS_SELECTOR, "h5, h4, .card-title, strong")
                if name_elem:
                    card_data['Name'] = name_elem.text.strip()
            except:
                pass
            
            # Get all text from the card
            card_text = card.text
            
            # Look for common patterns
            # Email pattern
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            email_match = re.search(email_pattern, card_text)
            if email_match:
                card_data['Email'] = email_match.group(0)
            
            # Phone number pattern (10 digits)
            phone_patterns = [
                r'\b\d{10}\b',  # Standard 10 digits
                r'\b\d{5}\s?\d{5}\b',  # 5 digits space 5 digits
                r'\b\d{4}\s?\d{3}\s?\d{3}\b'  # 4-3-3 format
            ]
            
            for pattern in phone_patterns:
                phone_match = re.search(pattern, card_text)
                if phone_match:
                    # Clean up formatting
                    phone = re.sub(r'\s+', '', phone_match.group(0))
                    card_data['Mobile Number'] = phone
                    break
            
            # Enrollment number pattern (K/digits/year)
            enrollment_pattern = r'\bK/\d+/\d+\b'
            enrollment_match = re.search(enrollment_pattern, card_text)
            if enrollment_match:
                card_data['Enrollment Number'] = enrollment_match.group(0)
            
            return card_data
        except Exception as e:
            logger.warning(f"Error extracting from card: {e}")
            return {}
    
    def extract_data_from_visible_modal(self):
        """Extract all fields from a currently visible modal."""
        all_data = {}

        try:
            # 0) Wait for and grab the visible modal
            modal = WebDriverWait(self.driver, 5).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".modal.show"))
            )

            # 1) Name from modal title
            try:
                title = modal.find_element(By.CSS_SELECTOR, ".modal-title").text.strip()
                all_data['Name'] = title
                logger.info(f"Found Name: {title}")
            except:
                pass

            # 2) One-line fields
            rows = modal.find_elements(By.CSS_SELECTOR, ".row.mt-3, .form-group, .row")
            for row in rows:
                try:
                    lbl = row.find_element(By.CSS_SELECTOR, "label, .col-form-label").text.strip()
                    val = row.find_element(By.CSS_SELECTOR, "div:nth-child(2), .col-md-6, .col-sm-8").text.strip()
                    logger.info(f"Row data – {lbl}: {val}")
                    if "Mobile" in lbl or "Phone" in lbl:
                        all_data['Mobile Number'] = val
                    elif "Email" in lbl:
                        all_data['Email'] = val
                    elif "Enrollment" in lbl or "Registration" in lbl:
                        all_data['Enrollment Number'] = val
                    # skip Office/Residence here
                except:
                    continue

            # 3) Multi-line addresses: grab the parent DIV that contains the address headers
            try:
                addr_container = modal.find_element(
                    By.XPATH,
                    # any div that has both headers underneath it
                    ".//div[.//u[normalize-space(text())='Office Address'] and .//u[normalize-space(text())='Residence Address:']]"
                )
                # pull all <p> inside that block, in document order
                p_elems = addr_container.find_elements(By.TAG_NAME, "p")
                texts = [p.text.strip() for p in p_elems if p.text.strip()]

                # 1) Find the split points
                office_idx = texts.index('Office Address')

                # strip the trailing ":" if present just in case
                res_header = 'Residence Address:' if 'Residence Address:' in texts else 'Residence Address'
                res_idx = texts.index(res_header)

                # 2) Slice out and join
                office_block = texts[office_idx + 1 : res_idx]
                residence_block = texts[res_idx + 1 : ]

                all_data['Office Address'] = ", ".join(office_block)
                all_data['Residence Address'] = ", ".join(residence_block)
                
            except Exception as e:
                logger.warning(f"Could not locate or parse address container: {e}")

            # 4) Fallback regex for anything missing (optional)...

            return all_data

        except Exception as e:
            logger.warning(f"Error extracting data from visible modal: {e}")
            return {}

        
    def extract_all_data_with_javascript(self, modal_id):
        """Use JavaScript to extract all fields from a modal."""
        if not modal_id:
            return {}
            
        if not modal_id.startswith('#'):
            modal_id = f"#{modal_id}"
        
        try:
            # Show the modal
            self.driver.execute_script(f"$('{modal_id}').modal('show');")
            time.sleep(1)
            
            # Execute JavaScript to extract all data
            js_script = f"""
            var modalElement = document.querySelector('{modal_id}');
            var data = {{}};
            
            // Get the title/name
            var title = modalElement.querySelector('.modal-title');
            if (title) {{
                data['Name'] = title.textContent.trim();
                console.log('Found Name: ' + data['Name']);
            }}
            
            // Extract all label-value pairs
            var rows = modalElement.querySelectorAll('.row.mb-3, .form-group, .row');
            for (var i = 0; i < rows.length; i++) {{
                var row = rows[i];
                var label = row.querySelector('label, .col-form-label');
                var value = row.querySelector('div:nth-child(2), .col-md-8, .col-sm-8');
                
                if (label && value) {{
                    var labelText = label.textContent.trim();
                    var valueText = value.textContent.trim();
                    
                    // Map to appropriate fields
                    if (labelText.includes('Mobile') || labelText.includes('Phone')) {{
                        data['Mobile Number'] = valueText;
                        console.log('Found Mobile Number: ' + valueText);
                    }}
                    else if (labelText.includes('Email')) {{
                        data['Email'] = valueText;
                        console.log('Found Email: ' + valueText);
                    }}
                    else if (labelText.includes('Enrollment') || labelText.includes('Registration')) {{
                        data['Enrollment Number'] = valueText;
                        console.log('Found Enrollment Number: ' + valueText);
                    }}
                    else if (labelText.includes('Office Address')) {{
                        data['Office Address'] = valueText;
                        console.log('Found Office Address: ' + valueText);
                    }}
                    else if (labelText.includes('Residence Address')) {{
                        data['Residence Address'] = valueText;
                        console.log('Found Residence Address: ' + valueText);
                    }}
                }}
            }}
            
            // Extract email with regex if not found
            if (!data['Email']) {{
                var allText = modalElement.textContent;
                var emailRegex = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}/;
                var match = allText.match(emailRegex);
                if (match) {{
                    data['Email'] = match[0];
                    console.log('Found Email via regex: ' + data['Email']);
                }}
            }}
            
            // Extract phone with regex if not found
            if (!data['Mobile Number']) {{
                var allText = modalElement.textContent;
                var phoneRegex = /\\b\\d{{10}}\\b/;
                var match = allText.match(phoneRegex);
                if (match) {{
                    data['Mobile Number'] = match[0];
                    console.log('Found Mobile Number via regex: ' + data['Mobile Number']);
                }}
            }}
            
            // Extract enrollment number with regex if not found
            if (!data['Enrollment Number']) {{
                var allText = modalElement.textContent;
                var enrollRegex = /K\\/\\d+\\/\\d+/;
                var match = allText.match(enrollRegex);
                if (match) {{
                    data['Enrollment Number'] = match[0];
                    console.log('Found Enrollment Number via regex: ' + data['Enrollment Number']);
                }}
            }}
            
            return data;
            """
            
            result = self.driver.execute_script(js_script)
            
            # Close the modal
            self.driver.execute_script(f"$('{modal_id}').modal('hide');")
            time.sleep(0.5)
    
            return result
        except Exception as e:
            logger.warning(f"JavaScript extraction error: {e}")
            return {}
    
    def extract_complete_data(self, card):
        """Extract all lawyer data using multiple approaches."""
        try:
            # Make sure all modals are closed first
            self.close_all_modals()
            
            # Step 1: Try to extract basic data from the card
            lawyer_data = self.extract_from_card(card)
            logger.info(f"Initial data from card: {lawyer_data}")
            
            # Find the modal button and ID
            try:
                view_profile_button = card.find_element(By.CSS_SELECTOR, "a.btn[data-toggle='modal'], a.btn-primary")
                modal_id = view_profile_button.get_attribute("data-target")
                if not modal_id:
                    logger.warning("No modal ID found on button")
            except Exception as e:
                logger.warning(f"Could not find modal button: {e}")
                # Return whatever data we have from the card
                return lawyer_data if lawyer_data.get('Name') else None
            
            logger.info(f"Found modal ID: {modal_id}")
            
            # Step 2: JavaScript extraction (most reliable and complete)
            js_data = self.extract_all_data_with_javascript(modal_id)
            
            # Merge with existing data, preferring JavaScript data
            for key, value in js_data.items():
                if value:  # Only update if value is not empty
                    lawyer_data[key] = value
            
            # Step 3: Try clicking the button and extracting from the visible modal
            try:
                # Clear modals again to be safe
                self.close_all_modals()
                
                # Click the button
                view_profile_button.click()
                time.sleep(1)
                
                # Extract from visible modal
                modal_data = self.extract_data_from_visible_modal()
                
                # Merge with existing data
                for key, value in modal_data.items():
                    if value and (key not in lawyer_data or not lawyer_data[key]):
                        lawyer_data[key] = value
                
                # Close the modal
                self.close_all_modals()
                
                logger.info(f"Data after modal extraction: {lawyer_data}")
            except Exception as e:
                logger.warning(f"Error in modal extraction: {e}")
            
            # Final check for data completeness
            field_status = []
            for field in ['Name', 'Mobile Number', 'Email', 'Enrollment Number', 'Office Address', 'Residence Address']:
                status = "✓" if field in lawyer_data and lawyer_data[field] else "✗"
                field_status.append(f"{field}: {status}")
            
            logger.info(f"Data extraction status: {', '.join(field_status)}")
            
            # Drop empty values
            lawyer_data = {k: v for k, v in lawyer_data.items() if v}
            
            return lawyer_data
            
        except Exception as e:
            logger.error(f"Error extracting complete data: {e}")
            return None
    
    # def detect_pagination(self):
    #     """Detect all pagination elements and determine max pages."""
    #     try:
    #         # Wait for pagination
    #         WebDriverWait(self.driver, 10).until(
    #             EC.presence_of_element_located((By.CSS_SELECTOR, ".pagination"))
    #         )
            
    #         # Find all pagination links
    #         pagination = self.driver.find_element(By.CSS_SELECTOR, ".pagination")
    #         page_links = pagination.find_elements(By.TAG_NAME, "a")
            
    #         # Extract page numbers
    #         page_numbers = []
    #         for link in page_links:
    #             try:
    #                 text = link.text.strip()
    #                 # If it's a number, add it to the list
    #                 if text.isdigit():
    #                     page_numbers.append(int(text))
    #             except:
    #                 pass
            
    #         if page_numbers:
    #             self.max_pages = max(page_numbers)
    #             logger.info(f"Detected {self.max_pages} total pages")
    #             return True
            
    #         # If we couldn't find numbered pages, try to find the "Last" link
    #         last_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'Last')]")
    #         if last_links:
    #             # Click the "Last" link to go to the last page (to find out how many pages there are)
    #             last_links[0].click()
    #             time.sleep(PAGE_LOAD_WAIT)
                
    #             # Now find active page number
    #             active_pages = self.driver.find_elements(By.CSS_SELECTOR, ".pagination .active")
    #             if active_pages:
    #                 active_text = active_pages[0].text.strip()
    #                 if active_text.isdigit():
    #                     self.max_pages = int(active_text)
    #                     logger.info(f"Found {self.max_pages} total pages via Last link")
                        
    #                     # Go back to page 1
    #                     self.driver.get(BASE_URL)
    #                     time.sleep(PAGE_LOAD_WAIT)
    #                     return True
            
    #         # If we still can't find max pages, default to 1
    #         logger.warning("Could not determine max pages, defaulting to only current page")
    #         self.max_pages = 1
    #         return False
            
    #     except Exception as e:
    #         logger.error(f"Error detecting pagination: {e}")
    #         self.max_pages = 1
    #         return False

    def detect_pagination(self):
        """Detect all pagination elements and determine max pages."""
        try:
            # 1) Wait for the pagination bar to show up
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".pagination"))
            )
            pagination = self.driver.find_element(By.CSS_SELECTOR, ".pagination")
            page_links = pagination.find_elements(By.TAG_NAME, "a")

            # 2) Pull any numeric pages you see (this will only be the first window)
            page_numbers = []
            for link in page_links:
                txt = link.text.strip()
                if txt.isdigit():
                    page_numbers.append(int(txt))
            visible_max = max(page_numbers) if page_numbers else 1

            # 3) Now see if there's a “Last ›” link, and if so parse its href for the real max
            last_links = [a for a in page_links if "Last ›" in a.text]
            if last_links:
                href = last_links[0].get_attribute("href")
                # parse out ?page= or /page/<num> from the URL
                import urllib.parse as _up
                parsed = _up.urlparse(href)
                qs = _up.parse_qs(parsed.query)
                if "page" in qs:
                    real_max = int(qs["page"][0])
                else:
                    # fallback: maybe it’s in the path as the last segment
                    try:
                        real_max = int(parsed.path.rstrip("/").split("/")[-1])
                    except:
                        real_max = visible_max
                self.max_pages = real_max
                logger.info(f"Detected last page via Last› link: {self.max_pages}")
            else:
                # no Last link? just use the visible maximum
                self.max_pages = visible_max
                logger.info(f"No Last› link. Using visible max page: {self.max_pages}")

            # initialize current_page
            self.current_page = 1
            return True

        except Exception as e:
            logger.error(f"Error detecting pagination: {e}")
            # fallback to 1 page only
            self.max_pages = 1
            self.current_page = 1
            return False

    
    # def go_to_page(self, page_number):
    #     """Navigate to a specific page number."""
    #     if page_number == 1:
    #         # For page 1, just go to the base URL
    #         self.driver.get(BASE_URL)
    #         time.sleep(PAGE_LOAD_WAIT)
    #         self.current_page = 1
    #         return True
        
    #     try:
    #         # First make sure we're on a page with pagination visible
    #         if self.driver.current_url != BASE_URL:
    #             self.driver.get(BASE_URL)
    #             time.sleep(PAGE_LOAD_WAIT)
            
    #         # Wait for pagination to load
    #         WebDriverWait(self.driver, 10).until(
    #             EC.presence_of_element_located((By.CSS_SELECTOR, ".pagination"))
    #         )
            
    #         # Find all page links
    #         pagination = self.driver.find_element(By.CSS_SELECTOR, ".pagination")
    #         page_links = pagination.find_elements(By.TAG_NAME, "a")
            
    #         # Try to find the exact page number first
    #         for link in page_links:
    #             if link.text.strip() == str(page_number):
    #                 logger.info(f"Found direct link to page {page_number}")
    #                 link.click()
    #                 time.sleep(PAGE_LOAD_WAIT)
    #                 self.current_page = page_number
    #                 return True
            
    #         # If we can't find the exact page number, try other strategies
            
    #         # 1. Is there a "Next" link we can use?
    #         next_links = [link for link in page_links if ">" in link.text and "Last" not in link.text]
    #         if next_links and self.current_page < page_number:
    #             logger.info(f"Using Next link to navigate toward page {page_number}")
    #             # Click Next until we reach our target page
    #             while self.current_page < page_number:
    #                 next_links[0].click()
    #                 time.sleep(PAGE_LOAD_WAIT)
    #                 self.current_page += 1
                    
    #                 # Update the pagination elements for the next iteration
    #                 pagination = self.driver.find_element(By.CSS_SELECTOR, ".pagination")
    #                 page_links = pagination.find_elements(By.TAG_NAME, "a")
    #                 next_links = [link for link in page_links if ">" in link.text and "Last" not in link.text]
                    
    #                 if not next_links:
    #                     break
                
    #             return self.current_page == page_number
            
    #         # 2. Is there a "Last" link we can use to jump ahead?
    #         if page_number == self.max_pages:
    #             last_links = [link for link in page_links if "Last" in link.text]
    #             if last_links:
    #                 logger.info("Using Last link to navigate to the last page")
    #                 last_links[0].click()
    #                 time.sleep(PAGE_LOAD_WAIT)
    #                 self.current_page = self.max_pages
    #                 return True
            
    #         # 3. Try using JavaScript
    #         try:
    #             logger.info(f"Attempting to navigate to page {page_number} using JavaScript")
    #             # Check if we can use page parameter in URL (common in pagination)
    #             page_url = f"{BASE_URL}?page={page_number}"
    #             self.driver.get(page_url)
    #             time.sleep(PAGE_LOAD_WAIT)
                
    #             # Verify we're on the correct page by checking active pagination
    #             pagination = self.driver.find_element(By.CSS_SELECTOR, ".pagination")
    #             active_pages = pagination.find_elements(By.CSS_SELECTOR, ".active")
    #             if active_pages and active_pages[0].text.strip() == str(page_number):
    #                 logger.info(f"Successfully navigated to page {page_number} via URL parameter")
    #                 self.current_page = page_number
    #                 return True
    #         except:
    #             pass
            
    #         logger.error(f"Failed to navigate to page {page_number}")
    #         return False
            
    #     except Exception as e:
    #         logger.error(f"Error navigating to page {page_number}: {e}")
    #         return False
    def go_to_page(self, page_number):
        """Navigate to a specific page number by clicking the Next (>) button."""
        # If asking for page 1, just reload the base URL
        if page_number == 1:
            self.driver.get(BASE_URL)
            time.sleep(PAGE_LOAD_WAIT)
            self.current_page = 1
            return True

        try:
            # Make sure pagination is present
            WebDriverWait(self.driver, PAGE_LOAD_WAIT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".pagination"))
            )
            pagination = self.driver.find_element(By.CSS_SELECTOR, ".pagination")

            # Locate the Next button (">"), skipping any “Last ›” link
            next_btn = pagination.find_element(
                By.XPATH,
                ".//a[normalize-space(text())='>' and not(contains(text(),'Last'))]"
            )

            # Click Next until we reach our target page or Next becomes disabled
            while self.current_page < page_number:
                # If the Next button is disabled, we can’t go further
                if "disabled" in next_btn.get_attribute("class"):
                    logger.error(f"Next button is disabled at page {self.current_page}. Cannot reach page {page_number}.")
                    return False

                logger.info(f"Clicking Next to go from page {self.current_page} → {self.current_page+1}")
                next_btn.click()
                time.sleep(PAGE_LOAD_WAIT)

                # Update our current_page and refresh the pagination object
                self.current_page += 1
                logger.info(f"Now on page {self.current_page}")

                pagination = self.driver.find_element(By.CSS_SELECTOR, ".pagination")
                next_btn = pagination.find_element(
                    By.XPATH,
                    ".//a[normalize-space(text())='>' and not(contains(text(),'Last'))]"
                )

            return True

        except Exception as e:
            logger.error(f"Error navigating to page {page_number} via Next button: {e}")
            return False

    
    def scrape_page(self):
        """Scrape all lawyers on the current page."""
        lawyers_scraped = 0
        
        try:
            # Wait for the page to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".card"))
            )
            
            # Close any modals that might be open
            self.close_all_modals()
            
            # Find all lawyer cards
            lawyer_cards = self.driver.find_elements(By.CSS_SELECTOR, ".card")
            logger.info(f"Found {len(lawyer_cards)} lawyer cards on page {self.current_page}")
            
            # Process each card
            for i, card in enumerate(lawyer_cards):
                try:
                    logger.info(f"Processing lawyer {i+1}/{len(lawyer_cards)} on page {self.current_page}")
                    
                    # Extract complete lawyer data
                    lawyer_data = self.extract_complete_data(card)
                    
                    if lawyer_data and 'Name' in lawyer_data:
                        # Save to CSV
                        if self.save_to_csv(lawyer_data):
                            lawyers_scraped += 1
                            logger.info(f"Successfully saved data for: {lawyer_data.get('Name', 'Unknown')}")
                        
                        # Short delay between lawyers
                        time.sleep(random.uniform(1, 2))
                    else:
                        logger.warning(f"Could not extract data for lawyer {i+1} on page {self.current_page}")
                
                except Exception as e:
                    logger.error(f"Error processing lawyer card {i+1} on page {self.current_page}: {e}")
                    
                    # Make sure no modals are open before continuing
                    self.close_all_modals()
                    continue
            
            return lawyers_scraped
            
        except Exception as e:
            logger.error(f"Error scraping page {self.current_page}: {e}")
            return 0
    
    def run(self):
        """Run the scraper with pagination support."""
        logger.info("Starting the Trivandrum Bar Association Lawyer Data Scraper with Pagination...")
        
        # Create CSV file
        self.create_csv_file()
        
        # Setup WebDriver
        if not self.setup_driver():
            logger.error("Failed to setup WebDriver. Exiting.")
            return
        
        try:
            # Navigate to the base URL
            logger.info(f"Navigating to {BASE_URL}")
            self.driver.get(BASE_URL)
            time.sleep(PAGE_LOAD_WAIT)  # Give enough time for the page to load
            
            # Detect pagination and total pages
            # self.detect_pagination()
            
            if self.max_pages <= 0:
                logger.warning("No pages detected, defaulting to 1 page")
                self.max_pages = 1
            
            logger.info(f"Will scrape {self.max_pages} pages in total")
            
            # Scrape each page
            for page_num in range(1, self.max_pages + 1):
                logger.info(f"==== Scraping Page {page_num}/{self.max_pages} ====")
                
                # Navigate to the page (page 1 is already loaded)
                if page_num > 1:
                    if not self.go_to_page(page_num):
                        logger.error(f"Failed to navigate to page {page_num}. Skipping.")
                        continue
                
                # Scrape the current page
                lawyers_scraped = self.scrape_page()
                self.total_lawyers_scraped += lawyers_scraped
                
                logger.info(f"Scraped {lawyers_scraped} lawyers from page {page_num}")
                logger.info(f"Total lawyers scraped so far: {self.total_lawyers_scraped}")
                
                # Add a short delay between pages
                if page_num < self.max_pages:
                    time.sleep(random.uniform(2, 3))
            
        except KeyboardInterrupt:
            logger.info("Scraping interrupted by user.")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
        finally:
            # Close the WebDriver
            if self.driver:
                self.driver.quit()
            
            logger.info("\n--- Scraping Complete ---")
            logger.info(f"Total lawyers scraped: {self.total_lawyers_scraped}")
            logger.info(f"Data saved to: {CSV_FILE}")


if __name__ == "__main__":
    scraper = PaginationScraper()
    scraper.run()
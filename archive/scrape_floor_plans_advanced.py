"""
Advanced Floor Plan Scraper with Database Integration

This version:
- Integrates with your PostgreSQL database
- Handles multiple real estate agent layouts
- Stores floor plan metadata
- Includes retry logic and error handling
- Provides progress tracking
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import requests
import time
from pathlib import Path
from datetime import datetime
import json
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('floor_plan_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AdvancedFloorPlanScraper:
    """
    Advanced scraper that handles various real estate agent websites
    """
    
    # Common patterns for finding floor plans
    PLANTEGNING_PATTERNS = [
        # Button/Link text patterns
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'plantegning')]",
        "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'plantegning')]",
        "//div[contains(translate(@class, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'plantegning')]",
        "//span[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'plantegning')]",
        
        # Tab patterns
        "//button[contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'plantegning')]",
        "//*[contains(@data-tab, 'plantegning') or contains(@data-tab, 'floor')]",
        
        # Floor plan in English
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'floor plan')]",
        "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'floor plan')]",
    ]
    
    IMAGE_PATTERNS = [
        # Direct image patterns
        "//img[contains(@src, 'plantegning')]",
        "//img[contains(translate(@alt, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'plantegning')]",
        "//img[contains(translate(@alt, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'floor')]",
        "//img[contains(@src, 'floor')]",
        
        # Common container patterns
        ".floor-plan img",
        ".plantegning img",
        "[class*='floor'] img",
        "[class*='plant'] img",
        ".gallery img",
        ".image-gallery img",
    ]
    
    def __init__(self, download_folder="floor_plans", headless=True):
        self.download_folder = Path(download_folder)
        self.download_folder.mkdir(exist_ok=True)
        
        # Setup Chrome
        chrome_options = webdriver.ChromeOptions()
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Use webdriver-manager to auto-download correct ChromeDriver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
        self.results = []
        
    def handle_cookie_popup(self):
        """Handle cookie consent popup if present"""
        cookie_patterns = [
            "//button[contains(text(), 'Accepter og luk')]",
            "//button[contains(text(), 'Accepter')]",
            "//button[contains(text(), 'Accept')]",
            ".cookie-consent button",
            "[class*='cookie'] button[class*='accept']",
        ]
        
        for pattern in cookie_patterns:
            try:
                if pattern.startswith("//"):
                    element = self.driver.find_element(By.XPATH, pattern)
                else:
                    element = self.driver.find_element(By.CSS_SELECTOR, pattern)
                
                element.click()
                logger.info("✓ Closed cookie consent popup")
                time.sleep(1)
                return True
            except:
                continue
        
        return False
    
    def click_plantegning_button(self):
        """Try multiple strategies to find and click the plantegning button"""
        for pattern in self.PLANTEGNING_PATTERNS:
            try:
                if pattern.startswith("//"):
                    # XPath
                    element = self.driver.find_element(By.XPATH, pattern)
                else:
                    # CSS Selector
                    element = self.driver.find_element(By.CSS_SELECTOR, pattern)
                
                # Scroll to element
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(0.5)
                
                # Try to click
                try:
                    element.click()
                except:
                    # Try JavaScript click if regular click fails
                    self.driver.execute_script("arguments[0].click();", element)
                
                logger.info(f"✓ Clicked plantegning element using pattern: {pattern[:50]}...")
                time.sleep(2)  # Wait for content to load
                return True
                
            except (NoSuchElementException, Exception):
                continue
        
        logger.warning("⚠️ Could not find plantegning button")
        return False
    
    def extract_images(self):
        """Extract all potential floor plan image URLs"""
        image_urls = set()
        
        # Try each image pattern
        for pattern in self.IMAGE_PATTERNS:
            try:
                if pattern.startswith("//"):
                    # XPath
                    elements = self.driver.find_elements(By.XPATH, pattern)
                else:
                    # CSS Selector
                    elements = self.driver.find_elements(By.CSS_SELECTOR, pattern)
                
                for elem in elements:
                    src = elem.get_attribute('src')
                    if src and src.startswith('http'):
                        # Filter out tiny images (likely icons)
                        try:
                            width = elem.get_attribute('width')
                            height = elem.get_attribute('height')
                            if width and height:
                                if int(width) < 100 or int(height) < 100:
                                    continue
                        except:
                            pass
                        
                        image_urls.add(src)
                        
            except Exception as e:
                logger.debug(f"Pattern {pattern[:30]}... failed: {e}")
                continue
        
        return list(image_urls)
    
    def download_file(self, url, property_id, index):
        """Download file with retry logic"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=30, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                response.raise_for_status()
                
                # Determine extension
                content_type = response.headers.get('content-type', '')
                if 'pdf' in content_type or url.lower().endswith('.pdf'):
                    ext = 'pdf'
                elif 'png' in content_type or url.lower().endswith('.png'):
                    ext = 'png'
                else:
                    ext = 'jpg'
                
                filename = f"{property_id}_floorplan_{index:02d}.{ext}"
                filepath = self.download_folder / filename
                
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                file_size = len(response.content)
                logger.info(f"✅ Downloaded: {filename} ({file_size:,} bytes)")
                
                return {
                    'filename': filename,
                    'filepath': str(filepath),
                    'size': file_size,
                    'url': url,
                    'extension': ext
                }
                
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️ Attempt {attempt + 1} failed, retrying: {e}")
                    time.sleep(2)
                else:
                    logger.error(f"❌ Failed after {max_retries} attempts: {e}")
                    return None
    
    def scrape_property(self, property_id, property_url, max_wait=15):
        """
        Scrape floor plans from a property page
        
        Returns dict with results
        """
        result = {
            'property_id': property_id,
            'url': property_url,
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'floor_plans': [],
            'error': None
        }
        
        logger.info(f"\n{'='*80}")
        logger.info(f"Scraping property: {property_id}")
        logger.info(f"URL: {property_url}")
        logger.info(f"{'='*80}\n")
        
        try:
            # Load page
            self.driver.get(property_url)
            time.sleep(3)
            
            # Handle cookie popup first
            self.handle_cookie_popup()
            
            # Take screenshot of initial page
            screenshot_path = self.download_folder / f"{property_id}_page_screenshot.png"
            self.driver.save_screenshot(str(screenshot_path))
            logger.info(f"📸 Saved page screenshot: {screenshot_path}")
            
            # Try to click plantegning button
            self.click_plantegning_button()
            
            # Extract images
            image_urls = self.extract_images()
            
            if not image_urls:
                logger.warning(f"⚠️ No floor plan images found for {property_id}")
                result['error'] = 'No floor plans found'
                return result
            
            logger.info(f"📊 Found {len(image_urls)} potential floor plan(s)")
            
            # Download each image
            for i, url in enumerate(image_urls):
                file_info = self.download_file(url, property_id, i)
                if file_info:
                    result['floor_plans'].append(file_info)
            
            result['success'] = len(result['floor_plans']) > 0
            logger.info(f"✅ Successfully downloaded {len(result['floor_plans'])} floor plan(s)")
            
        except Exception as e:
            logger.error(f"❌ Error scraping {property_id}: {e}")
            result['error'] = str(e)
        
        self.results.append(result)
        return result
    
    def scrape_from_database(self, limit=10, offset=0):
        """
        Scrape floor plans for properties in database
        """
        from src.database import db
        from src.db_models import PropertyDB
        
        logger.info(f"\n🚀 Starting database scrape (limit={limit}, offset={offset})")
        
        session = db.get_session()
        properties = session.query(PropertyDB).offset(offset).limit(limit).all()
        
        logger.info(f"Found {len(properties)} properties to scrape\n")
        
        for i, prop in enumerate(properties, 1):
            logger.info(f"\n[{i}/{len(properties)}] Processing property...")
            
            url = f"https://www.boligsiden.dk/addresses/{prop.id}"
            self.scrape_property(prop.id, url)
            
            # Be polite
            if i < len(properties):
                time.sleep(3)
        
        session.close()
        
        # Save results
        self.save_results()
        self.print_summary()
        
        return self.results
    
    def save_results(self):
        """Save scraping results to JSON"""
        results_file = self.download_folder / f"scraping_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n💾 Results saved to: {results_file}")
    
    def print_summary(self):
        """Print summary of scraping session"""
        total = len(self.results)
        successful = sum(1 for r in self.results if r['success'])
        total_files = sum(len(r['floor_plans']) for r in self.results)
        
        logger.info(f"\n{'='*80}")
        logger.info("SCRAPING SUMMARY")
        logger.info(f"{'='*80}")
        logger.info(f"Total properties processed: {total}")
        logger.info(f"Successful: {successful} ({successful/total*100:.1f}%)")
        logger.info(f"Failed: {total - successful}")
        logger.info(f"Total floor plans downloaded: {total_files}")
        logger.info(f"Download folder: {self.download_folder.absolute()}")
        logger.info(f"{'='*80}\n")
    
    def close(self):
        """Close browser"""
        self.driver.quit()
        logger.info("🔒 Browser closed")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape floor plans from Boligsiden.dk')
    parser.add_argument('--limit', type=int, default=5, help='Number of properties to scrape')
    parser.add_argument('--offset', type=int, default=0, help='Offset for database query')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--folder', type=str, default='floor_plans', help='Download folder')
    
    args = parser.parse_args()
    
    scraper = AdvancedFloorPlanScraper(
        download_folder=args.folder,
        headless=args.headless
    )
    
    try:
        scraper.scrape_from_database(limit=args.limit, offset=args.offset)
    finally:
        scraper.close()

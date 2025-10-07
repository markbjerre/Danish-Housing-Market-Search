"""
Floor Plan (Plantegning) Scraper for Boligsiden.dk

This script attempts to automatically download floor plans from Boligsiden property pages.
It handles dynamic content and various real estate agent layouts.

Requirements:
    pip install selenium pillow requests
    
You'll also need ChromeDriver: https://chromedriver.chromium.org/
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import requests
import time
import os
from pathlib import Path
from urllib.parse import urljoin
import re

class FloorPlanScraper:
    def __init__(self, download_folder="floor_plans"):
        """Initialize the scraper with download folder"""
        self.download_folder = Path(download_folder)
        self.download_folder.mkdir(exist_ok=True)
        
        # Setup Chrome options
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')  # Run in background
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
        
    def handle_cookie_popup(self):
        """Handle cookie consent popup if present"""
        try:
            accept_btn = self.driver.find_element(
                By.XPATH,
                "//button[contains(text(), 'Accepter og luk') or contains(text(), 'Accepter')]"
            )
            accept_btn.click()
            time.sleep(1)
            print("✓ Closed cookie popup")
        except:
            pass  # No popup
    
    def find_floor_plan_elements(self):
        """
        Try multiple methods to find floor plan images/links
        Returns list of image URLs
        """
        floor_plan_urls = []
        
        # Strategy 1: Look for "Plantegninger" button and click it
        try:
            plantegning_button = self.driver.find_element(
                By.XPATH, 
                "//button[contains(text(), 'PLANTEGNINGER')] | //a[contains(text(), 'Plantegninger')] | //div[contains(text(), 'Plantegninger')]"
            )
            plantegning_button.click()
            time.sleep(2)  # Wait for content to load
            print("✓ Found and clicked Plantegninger button")
        except NoSuchElementException:
            print("ℹ️ No Plantegninger button found, trying direct search")
        
        # Strategy 2: Look for images with 'plantegning' in src or alt
        try:
            images = self.driver.find_elements(
                By.XPATH,
                "//img[contains(@src, 'plantegning') or contains(@alt, 'plantegning') or contains(@alt, 'floor') or contains(@title, 'plantegning')]"
            )
            for img in images:
                src = img.get_attribute('src')
                if src:
                    floor_plan_urls.append(src)
                    print(f"✓ Found floor plan image: {src[:80]}...")
        except Exception as e:
            print(f"⚠️ Error finding images: {e}")
        
        # Strategy 3: Look in modal/lightbox that may have opened
        try:
            modal_images = self.driver.find_elements(
                By.CSS_SELECTOR,
                ".modal img, .lightbox img, .gallery img, [class*='floor'] img, [class*='plant'] img"
            )
            for img in modal_images:
                src = img.get_attribute('src')
                if src and src not in floor_plan_urls:
                    floor_plan_urls.append(src)
                    print(f"✓ Found modal floor plan: {src[:80]}...")
        except Exception as e:
            print(f"⚠️ Error finding modal images: {e}")
        
        # Strategy 4: Look for PDF links (some floor plans are PDFs)
        try:
            pdf_links = self.driver.find_elements(
                By.XPATH,
                "//a[contains(@href, '.pdf') and (contains(text(), 'plantegning') or contains(text(), 'Plantegning'))]"
            )
            for link in pdf_links:
                href = link.get_attribute('href')
                if href:
                    floor_plan_urls.append(href)
                    print(f"✓ Found PDF floor plan: {href[:80]}...")
        except Exception as e:
            print(f"⚠️ Error finding PDFs: {e}")
        
        return floor_plan_urls
    
    def download_image(self, url, property_id, index=0):
        """Download an image from URL"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Determine file extension
            if url.lower().endswith('.pdf'):
                ext = 'pdf'
            elif url.lower().endswith('.png'):
                ext = 'png'
            else:
                ext = 'jpg'
            
            filename = f"{property_id}_floorplan_{index}.{ext}"
            filepath = self.download_folder / filename
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ Downloaded: {filename} ({len(response.content)} bytes)")
            return filepath
        
        except Exception as e:
            print(f"❌ Failed to download {url}: {e}")
            return None
    
    def scrape_property(self, property_url, property_id):
        """
        Scrape floor plans from a single property page
        
        Args:
            property_url: Full URL to property page
            property_id: Unique ID for saving files
            
        Returns:
            List of downloaded file paths
        """
        print(f"\n{'='*80}")
        print(f"Scraping: {property_url}")
        print(f"Property ID: {property_id}")
        print(f"{'='*80}\n")
        
        downloaded_files = []
        
        try:
            # Load the page
            self.driver.get(property_url)
            time.sleep(3)  # Wait for page to load
            
            # Handle cookie popup
            self.handle_cookie_popup()
            
            # Try to find floor plan elements
            floor_plan_urls = self.find_floor_plan_elements()
            
            if not floor_plan_urls:
                print("⚠️ No floor plans found on this page")
                return downloaded_files
            
            print(f"\n📊 Found {len(floor_plan_urls)} floor plan(s)")
            
            # Download each floor plan
            for i, url in enumerate(floor_plan_urls):
                filepath = self.download_image(url, property_id, i)
                if filepath:
                    downloaded_files.append(filepath)
            
            print(f"\n✅ Successfully downloaded {len(downloaded_files)} floor plan(s)")
            
        except Exception as e:
            print(f"❌ Error scraping property: {e}")
        
        return downloaded_files
    
    def scrape_multiple_properties(self, property_data):
        """
        Scrape floor plans from multiple properties
        
        Args:
            property_data: List of tuples [(property_id, property_url), ...]
        """
        results = {}
        
        print(f"\n🏁 Starting batch scrape of {len(property_data)} properties")
        print(f"Download folder: {self.download_folder.absolute()}\n")
        
        for i, (prop_id, prop_url) in enumerate(property_data, 1):
            print(f"\n[{i}/{len(property_data)}] Processing property...")
            
            files = self.scrape_property(prop_url, prop_id)
            results[prop_id] = files
            
            # Be polite - wait between requests
            if i < len(property_data):
                time.sleep(2)
        
        # Summary
        print(f"\n{'='*80}")
        print("SCRAPING COMPLETE")
        print(f"{'='*80}")
        total_files = sum(len(files) for files in results.values())
        print(f"Total properties processed: {len(property_data)}")
        print(f"Total floor plans downloaded: {total_files}")
        print(f"Files saved to: {self.download_folder.absolute()}")
        
        return results
    
    def close(self):
        """Close the browser"""
        self.driver.quit()
        print("\n🔒 Browser closed")


# Example usage
if __name__ == "__main__":
    # Example: Scrape floor plans from database
    from src.database import db
    from src.db_models import PropertyDB
    
    # Get sample properties
    session = db.get_session()
    properties = session.query(PropertyDB).limit(5).all()
    
    # Prepare data
    property_data = [
        (prop.id, f"https://www.boligsiden.dk/addresses/{prop.id}")
        for prop in properties
    ]
    
    session.close()
    
    # Create scraper and run
    scraper = FloorPlanScraper(download_folder="floor_plans")
    
    try:
        results = scraper.scrape_multiple_properties(property_data)
        
        # Print results
        print("\n📋 Detailed Results:")
        for prop_id, files in results.items():
            if files:
                print(f"\n{prop_id}:")
                for f in files:
                    print(f"  ✓ {f}")
            else:
                print(f"\n{prop_id}: No floor plans found")
    
    finally:
        scraper.close()

from flask import Flask, request, jsonify
import requests
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import threading
from datetime import datetime
import logging
import re
import os
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz
from textdistance import levenshtein
from unidecode import unidecode
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)
import asyncio
from playwright.sync_api import sync_playwright

# Railway configuration
PORT = int(os.environ.get('PORT', 5000))
CONTACT_SERVER_URL = os.environ.get('CONTACT_SERVER_URL', 'http://127.0.0.1:5001')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class AdvancedDataExtractor:
    """Advanced data extraction and classification"""
    
    def __init__(self):
        self.address_keywords = [
            'street', 'road', 'block', 'phase', 'sector', 'avenue', 'colony', 
            'extension', 'market', 'plaza', 'building', 'area', 'town', 'plot', 
            'lane', 'blvd', 'boulevard', 'main', 'mall', 'center', 'square',
            'park', 'garden', 'society', 'scheme', 'housing', 'commercial'
        ]
        
        self.category_keywords = [
            'agency', 'service', 'company', 'store', 'shop', 'center', 'rental',
            'tour', 'office', 'business', 'enterprise', 'corporation', 'firm',
            'services', 'solutions', 'group', 'associates', 'consultancy'
        ]
        
        self.phone_patterns = [
            r'(\+92[\s\-]?\d{3}[\s\-]?\d{7})',  # Pakistan international
            r'(\d{4}[\s\-]?\d{7})',  # Local 11-digit
            r'(\+92[\s\-]?\d{2}[\s\-]?\d{8})',  # Alternative Pakistan format
            r'(\d{3}[\s\-]?\d{7})',  # 10-digit local
            r'(\+?\d{2,4}[\s\-]?\d{3}[\s\-]?\d{4,7})'  # General international
        ]
        
        self.url_patterns = [
            r'(https?://[\w\.-]+(?:\.[a-z]{2,})+(?:/[\w\.-]*)*)',
            r'(www\.[\w\.-]+(?:\.[a-z]{2,})+(?:/[\w\.-]*)*)',
            r'([\w\.-]+\.(?:com|net|org|pk|co\.uk|info|biz)(?:/[\w\.-]*)*)'
        ]
    
    def classify_text_line(self, line, business_name):
        """Classify a text line as address, category, or other"""
        line_lower = line.lower().strip()
        business_name_lower = business_name.lower().strip()
        
        # Skip if it's the business name
        if self.is_similar_text(line_lower, business_name_lower, threshold=0.8):
            return 'duplicate'
        
        # Skip rating/review lines
        if re.search(r'\d+\.?\d*\s*(?:stars?|\(?\d+\)?)', line):
            return 'rating_review'
        
        # Check for address indicators
        address_score = sum(1 for keyword in self.address_keywords if keyword in line_lower)
        category_score = sum(1 for keyword in self.category_keywords if keyword in line_lower)
        
        # Address patterns (codes, numbers, specific formatting)
        has_address_patterns = bool(re.search(r'[A-Z]\d+[A-Z]*[\+\-]?\d*[A-Z]*|#\s*\w+|\d+[A-Z]?\s*[,-]\s*|plot\s*\d+|block\s*[A-Z]', line, re.I))
        
        # Category patterns
        has_category_patterns = bool(re.search(r'(car\s+rental|rental\s+car|agency|service|company|tour)', line_lower))
        
        if address_score > category_score and (has_address_patterns or len(line) > 15):
            return 'address'
        elif category_score > 0 or has_category_patterns:
            return 'category'
        elif has_address_patterns and len(line) > 10:
            return 'address'
        else:
            return 'other'
    
    def is_similar_text(self, text1, text2, threshold=0.7):
        """Check if two texts are similar using fuzzy matching"""
        return fuzz.ratio(text1, text2) > (threshold * 100)
    
    def extract_phone_numbers(self, text):
        """Extract phone numbers with multiple patterns"""
        phones = []
        for pattern in self.phone_patterns:
            matches = re.findall(pattern, text)
            phones.extend(matches)
        
        # Clean and validate phone numbers
        clean_phones = []
        for phone in phones:
            clean_phone = re.sub(r'[^\d\+\-\s\(\)]', '', phone).strip()
            if len(re.sub(r'[^\d]', '', clean_phone)) >= 7:  # At least 7 digits
                clean_phones.append(clean_phone)
        
        return clean_phones
    
    def extract_websites(self, text):
        """Extract websites with multiple patterns"""
        websites = []
        for pattern in self.url_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if 'google.com' not in match and 'maps' not in match:
                    if not match.startswith('http'):
                        match = 'https://' + match
                    websites.append(match)
        return websites
    
    def clean_address(self, address, business_name):
        """Clean and validate address"""
        if not address or len(address) < 5:
            return ''
        
        # Remove business name from address if it appears
        if self.is_similar_text(address.lower(), business_name.lower(), threshold=0.8):
            return ''
        
        # Clean up common prefixes
        address = re.sub(r'^(car rental agency|agency|service|company)\s*[·•]\s*', '', address, flags=re.I)
        
        # Clean whitespace and formatting
        address = re.sub(r'\s+', ' ', address).strip()
        
        return address[:200] if len(address) > 10 else ''
    
    def clean_category(self, category, business_name):
        """Clean and standardize category"""
        if not category:
            return 'Car Rental Agency'
        
        # Extract just the category type
        category_match = re.search(r'(car rental agency|rental agency|agency|service|company|store|shop|center|rental|tour|office)', category, re.IGNORECASE)
        if category_match:
            return category_match.group(1).title()
        
        # Clean up and return first meaningful part
        clean_cat = re.sub(r'^(car rental agency|agency|service|company)\s*[·•]\s*', '', category, flags=re.I)
        clean_cat = re.sub(r'\s+', ' ', clean_cat).strip()
        
        return clean_cat[:50] if clean_cat else 'Car Rental Agency'

    def is_review_line(self, line):
        # Simple review/testimonial detection
        review_keywords = [
            'clean', 'well-maintained', 'exceeded my expectations', 'recommend', 'experience', 'service',
            'driver', 'comfortable', 'excellent', 'friendly', 'punctual', 'satisfied', 'thank you', 'amazing',
            'best', 'worst', 'awesome', 'great', 'bad', 'good', 'helpful', 'support', 'customer', 'review', 'testimonial'
        ]
        line_lower = line.lower()
        if any(word in line_lower for word in review_keywords):
            return True
        # Sentiment-based: if line contains many adjectives
        words = word_tokenize(line_lower)
        stop_words = set(stopwords.words('english'))
        non_stop = [w for w in words if w.isalpha() and w not in stop_words]
        if len(non_stop) > 0 and sum(1 for w in non_stop if w.endswith('ed') or w.endswith('ful') or w.endswith('ive')) > 1:
            return True
        return False

    def extract_social_media(self, text):
        """Extract social media patterns from text"""
        social_patterns = {
            'facebook': [
                r'facebook\.com/[\w\.-]+',
                r'fb\.com/[\w\.-]+',
                r'facebook\.com/pages/[\w\.-]+'
            ],
            'instagram': [
                r'instagram\.com/[\w\.-]+',
                r'ig\.com/[\w\.-]+'
            ],
            'twitter': [
                r'twitter\.com/[\w\.-]+',
                r'x\.com/[\w\.-]+'
            ],
            'linkedin': [
                r'linkedin\.com/company/[\w\.-]+',
                r'linkedin\.com/in/[\w\.-]+'
            ],
            'youtube': [
                r'youtube\.com/[\w\.-]+',
                r'youtu\.be/[\w\.-]+'
            ],
            'whatsapp': [
                r'wa\.me/[\d\+]+',
                r'whatsapp\.com/[\w\.-]+'
            ]
        }
        
        social_data = {}
        for platform, patterns in social_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    social_data[platform] = matches[0]
                    break
        
        return social_data

    def extract_emails_advanced(self, text):
        """Advanced email extraction with validation"""
        email_patterns = [
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            r'[a-zA-Z0-9._%+-]+\s*@\s*[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            r'[a-zA-Z0-9._%+-]+\s*\[at\]\s*[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        ]
        
        emails = []
        for pattern in email_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                clean_email = re.sub(r'\s+', '', match.replace('[at]', '@'))
                if self.is_valid_email(clean_email):
                    emails.append(clean_email)
        
        return list(set(emails))

    def is_valid_email(self, email):
        """Validate email format"""
        if not email or len(email) < 5:
            return False
        
        # Check for common false positives
        invalid_domains = ['example.com', 'test.com', 'google.com', 'gmail.com']
        domain = email.split('@')[-1] if '@' in email else ''
        
        if domain in invalid_domains:
            return False
        
        # Basic email validation
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_regex, email))

    def clean_social_url(self, url):
        """Clean and validate social media URLs"""
        if not url:
            return ""
        
        # Ensure proper formatting
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            url = 'https://' + url.lstrip('/')
        elif not url.startswith('http'):
            url = 'https://' + url
        
        return url.strip()

    def clean_email(self, email):
        """Clean and validate email"""
        if not email:
            return ""
        
        email = email.replace('mailto:', '').strip().lower()
        
        # Basic validation
        if '@' not in email or len(email) < 5:
            return ""
        
        # Remove invalid domains
        invalid_domains = ['example.com', 'test.com', 'google.com']
        domain = email.split('@')[-1]
        if domain in invalid_domains:
            return ""
        
        return email

class GoogleMapsScraper:
    def __init__(self):
        # Load settings from file if available
        self.settings = self.load_settings()
        self.data_extractor = AdvancedDataExtractor()
        
        # No Selenium options needed for Playwright
        self.chrome_options = Options()
        if self.settings["headless_mode"]:
            self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
        
        if not self.settings["enable_gpu"]:
            self.chrome_options.add_argument("--disable-gpu")
        
        self.chrome_options.add_argument(f"--window-size={self.settings['window_width']},{self.settings['window_height']}")
        
        # Enhanced Chrome options for better performance
        self.chrome_options.add_argument("--disable-extensions")
        self.chrome_options.add_argument("--disable-plugins")
        self.chrome_options.add_argument("--disable-images")  # Faster loading
        self.chrome_options.add_argument("--disable-javascript")  # We'll enable it when needed
        
        # User agents for rotation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        
        self.driver = None
        
        # Set logging level based on debug mode
        if self.settings["debug_mode"]:
            logging.getLogger(__name__).setLevel(logging.DEBUG)
    
    def load_settings(self):
        """Load settings from configuration file"""
        default_settings = {
            "headless_mode": True,
            "window_width": 1920,
            "window_height": 1080,
            "page_load_wait": 8,
            "results_wait": 25,
            "scroll_attempts": 30,  # Increased from 20
            "scroll_delay": 1.0,    # Reduced from 1.5 for faster scrolling
            "extraction_delay": 0.2,
            "max_retries": 5,
            "default_zoom_level": 13,  # Reduced from 14 for wider coverage
            "user_agent_rotation": True,
            "enable_gpu": False,
            "debug_mode": False
        }
        
        try:
            if os.path.exists("scraper_settings.json"):
                with open("scraper_settings.json", "r") as f:
                    loaded_settings = json.load(f)
                    default_settings.update(loaded_settings)
                    logger.info("Loaded custom settings from scraper_settings.json")
        except Exception as e:
            logger.warning(f"Failed to load settings, using defaults: {e}")
        
        return default_settings
    
    def start_driver(self):
        """Initialize Chrome WebDriver"""
        if self.settings["user_agent_rotation"]:
            import random
            user_agent = random.choice(self.user_agents)
            self.chrome_options.add_argument(f"--user-agent={user_agent}")
        
        self.driver = webdriver.Chrome(options=self.chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        logger.info("Chrome driver started successfully")
    
    def build_maps_url(self, search_term, latitude, longitude, radius_km=5):
        """Build Google Maps search URL"""
        # Clean search term
        search_formatted = search_term.lower().replace(' ', '+').replace('-', '+')
        
        # Determine zoom based on radius (use setting as base)
        zoom_level = self.settings["default_zoom_level"]
        if radius_km <= 2:
            zoom_level = 16
        elif radius_km <= 4:
            zoom_level = 15
        elif radius_km >= 20:
            zoom_level = 12
        elif radius_km >= 50:
            zoom_level = 10
        
        url = f"https://www.google.com/maps/search/{search_formatted}/@{latitude},{longitude},{zoom_level}z"
        logger.info(f"Generated URL: {url}")
        return url
    
    def safe_get_text(self, element, max_retries=None):
        """Safely get text from element with retry logic"""
        if max_retries is None:
            max_retries = self.settings["max_retries"]
            
        for attempt in range(max_retries):
            try:
                return element.text.strip()
            except StaleElementReferenceException:
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                return ""
            except Exception:
                return ""
        return ""
    
    def safe_find_element(self, parent, selector, max_retries=None):
        """Safely find element with retry logic"""
        if max_retries is None:
            max_retries = self.settings["max_retries"]
            
        for attempt in range(max_retries):
            try:
                return parent.find_element(By.CSS_SELECTOR, selector)
            except (StaleElementReferenceException, NoSuchElementException):
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                return None
        return None
    
    def scrape_businesses(self, search_term, area_name, latitude, longitude, radius_km=5, max_results=30):
        """Advanced Playwright scraping with Chrome extension methodology"""
        url = self.build_maps_url(search_term, latitude, longitude, radius_km)
        logger.info(f"Scraping {search_term} in {area_name} using advanced Playwright")
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=self.settings["headless_mode"],
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
                page = browser.new_page()
                
                # Set user agent to avoid detection
                page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                })
                
                page.goto(url, wait_until='domcontentloaded')
                page.wait_for_timeout(self.settings["page_load_wait"] * 1000)
                
                # Capture console logs
                page.on("console", lambda msg: logger.info(f"Browser: {msg.text}"))
                
                # Wait for results panel to load
                try:
                    page.wait_for_selector('[role="main"]', timeout=10000)
                    logger.info("Results panel loaded successfully")
                except:
                    logger.warning("Results panel timeout, continuing anyway")
                
                # Enhanced scrolling to load all results
                logger.info("Starting enhanced scrolling to load all businesses")
                previous_count = 0
                no_change_count = 0
                
                for scroll_attempt in range(self.settings["scroll_attempts"] * 3):  # Triple scroll attempts
                    # Scroll the results panel specifically
                    page.evaluate('''
                        const resultsPanel = document.querySelector('[role="main"]') || document.querySelector('.siAUzd') || document.querySelector('.m6QErb');
                        if (resultsPanel) {
                            resultsPanel.scrollTop = resultsPanel.scrollHeight;
                        } else {
                            window.scrollBy(0, 1000);
                        }
                    ''')
                    page.wait_for_timeout(self.settings["scroll_delay"] * 1000)
                    
                    # Check current business count
                    current_count = page.evaluate('''
                        () => {
                            const cards = document.querySelectorAll('[data-result-index], .Nv2PK, .lI9IFe, .bfdHYd, .qjESne, .THOPZb, .VfPpkd-rymPhb-ibnC6b');
                            return cards.length;
                        }
                    ''')
                    
                    logger.info(f"Scroll {scroll_attempt + 1}: Found {current_count} businesses")
                    
                    # Check if "End of list" appears
                    end_of_list = page.query_selector('text="You\'ve reached the end of the list."')
                    if end_of_list:
                        logger.info(f"Reached end of list after {scroll_attempt + 1} scrolls")
                        break
                    
                    # Check for no progress
                    if current_count == previous_count:
                        no_change_count += 1
                        if no_change_count >= 5:
                            logger.info(f"No new businesses found after {no_change_count} scrolls, trying alternative scrolling")
                            # Try alternative scrolling methods
                            page.evaluate('''
                                // Try scrolling the entire page
                                window.scrollTo(0, document.body.scrollHeight);
                                // Try scrolling multiple containers
                                const containers = document.querySelectorAll('[role="main"], .m6QErb, .siAUzd, .TFQHme');
                                containers.forEach(container => {
                                    container.scrollTop = container.scrollHeight;
                                });
                            ''')
                            page.wait_for_timeout(2000)
                            
                            # Check again
                            new_count = page.evaluate('''
                                () => {
                                    const cards = document.querySelectorAll('[data-result-index], .Nv2PK, .lI9IFe, .bfdHYd, .qjESne, .THOPZb, .VfPpkd-rymPhb-ibnC6b');
                                    return cards.length;
                                }
                            ''')
                            
                            if new_count > current_count:
                                logger.info(f"Alternative scrolling worked: {new_count} businesses")
                                no_change_count = 0
                                current_count = new_count
                            elif no_change_count >= 10:
                                logger.info(f"Stopping after {scroll_attempt + 1} scrolls - no more results")
                                break
                    else:
                        no_change_count = 0
                        previous_count = current_count
                    
                    # Stop if we have enough diverse results
                    if current_count >= max_results * 2:  # Allow for duplicates
                        logger.info(f"Reached target of {current_count} businesses")
                        break
                
                # Advanced business extraction using multiple strategies
                businesses_data = page.evaluate('''
                    () => {
                        const businesses = [];
                        const processedNames = new Set(); // Prevent duplicates
                        
                        // Strategy 1: Main business cards with more selectors
                        const businessCards = document.querySelectorAll('[data-result-index], .Nv2PK, .lI9IFe, .bfdHYd, .qjESne, .THOPZb, .VfPpkd-rymPhb-ibnC6b');
                        
                        console.log(`Found ${businessCards.length} business cards`);
                        
                        businessCards.forEach((card, index) => {
                            try {
                                // Extract basic info with more selectors
                                const nameSelectors = ['h3', '.fontHeadlineSmall', '.qBF1Pd', '.NrDZNb', '.fontHeadlineMedium', '.fontBodyLarge', '.fontTitleLarge'];
                                let name = '';
                                for (const selector of nameSelectors) {
                                    const nameEl = card.querySelector(selector);
                                    if (nameEl && nameEl.innerText.trim()) {
                                        name = nameEl.innerText.trim();
                                        break;
                                    }
                                }
                                
                                console.log(`Card ${index}: Name = "${name}"`);
                                
                                if (!name) {
                                    console.log(`Card ${index}: Skipping - no name found`);
                                    return;
                                }
                                
                                // More lenient duplicate checking - allow similar but not identical names
                                let isDuplicate = false;
                                for (const existingName of processedNames) {
                                    if (name.toLowerCase() === existingName.toLowerCase()) {
                                        isDuplicate = true;
                                        break;
                                    }
                                    // Only check for exact matches or very close matches (not substring matches)
                                    if (name.toLowerCase().replace(/[^a-z0-9]/g, '') === existingName.toLowerCase().replace(/[^a-z0-9]/g, '')) {
                                        isDuplicate = true;
                                        break;
                                    }
                                }
                                
                                if (isDuplicate) {
                                    console.log(`Card ${index}: Skipping - duplicate name "${name}"`);
                                    return;
                                }
                                
                                processedNames.add(name);
                                
                                // Extract rating and reviews with more selectors
                                const ratingSelectors = ['.MW4etd', '.KFi5wf', '[data-value="Rating"]', '.F7nice', '.fontDisplayLarge', '.fontBodyMedium'];
                                let rating = '';
                                for (const selector of ratingSelectors) {
                                    const ratingEl = card.querySelector(selector);
                                    if (ratingEl && ratingEl.innerText.trim()) {
                                        rating = ratingEl.innerText.trim();
                                        break;
                                    }
                                }
                                
                                const reviewSelectors = ['.UY7F9', '.HHrUdb', '.z5jxId', '.fontBodyMedium'];
                                let reviewCount = '';
                                for (const selector of reviewSelectors) {
                                    const reviewEl = card.querySelector(selector);
                                    if (reviewEl && reviewEl.innerText.trim()) {
                                        reviewCount = reviewEl.innerText.trim();
                                        break;
                                    }
                                }
                                
                                // Get all text content for parsing
                                const allText = card.innerText;
                                const textLines = allText.split('\\n').map(line => line.trim()).filter(line => line);
                                
                                // Extract phone using regex from all text
                                const phoneRegex = /(?:\\+92|0)?\\s?3\\d{2}\\s?\\d{7}|(?:\\+92|0)?\\s?\\d{2,4}\\s?\\d{7,8}/g;
                                const phoneMatches = allText.match(phoneRegex);
                                const phone = phoneMatches ? phoneMatches[0].trim() : '';
                                
                                // Extract category and address intelligently
                                let category = '';
                                let address = '';
                                
                                // Look for category indicators
                                const categoryKeywords = ['rental', 'agency', 'service', 'tours', 'car', 'luxury', 'transport', 'vehicle'];
                                const addressKeywords = ['street', 'block', 'phase', 'dha', 'office', 'building', 'sector', 'area'];
                                
                                for (const line of textLines) {
                                    const lowerLine = line.toLowerCase();
                                    
                                    if (!category && categoryKeywords.some(keyword => lowerLine.includes(keyword)) && !addressKeywords.some(keyword => lowerLine.includes(keyword))) {
                                        category = line;
                                    } else if (!address && (addressKeywords.some(keyword => lowerLine.includes(keyword)) || /\\d+/.test(line)) && !lowerLine.includes('hour') && !lowerLine.includes('star')) {
                                        address = line;
                                    }
                                }
                                
                                // Fallback: use data attributes
                                if (!address) {
                                    const addressSelectors = ['[data-value="Address"]', '.LrzXr', '.W4Efsd:last-child', '.rogA2c', '.fontBodyMedium'];
                                    for (const selector of addressSelectors) {
                                        const addressEl = card.querySelector(selector);
                                        if (addressEl && addressEl.innerText.trim()) {
                                            address = addressEl.innerText.trim();
                                            break;
                                        }
                                    }
                                }
                                
                                if (!category) {
                                    const categorySelectors = ['.DkEaL', '.W4Efsd:first-child', '.YhemCb'];
                                    for (const selector of categorySelectors) {
                                        const categoryEl = card.querySelector(selector);
                                        if (categoryEl && categoryEl.innerText.trim()) {
                                            category = categoryEl.innerText.trim();
                                            break;
                                        }
                                    }
                                    if (!category) category = 'Car Rental Agency';
                                }
                                
                                // More lenient extraction - include even if missing some fields
                                if (name && name.length > 2) {
                                    businesses.push({
                                        name: name,
                                        rating: rating,
                                        reviewCount: reviewCount,
                                        phone: phone,
                                        category: category,
                                        address: address,
                                        rawText: allText,
                                        elementIndex: index
                                    });
                                    console.log(`Card ${index}: Added business "${name}"`);
                                } else {
                                    console.log(`Card ${index}: Skipping - invalid name "${name}"`);
                                }
                                
                            } catch (error) {
                                console.log(`Error processing business card ${index}:`, error);
                            }
                        });
                        
                        console.log(`Total businesses extracted: ${businesses.length}`);
                        
                        // Fallback: Try alternative selectors if we found too few businesses
                        if (businesses.length < 15) {
                            console.log('Trying fallback extraction...');
                            const fallbackCards = document.querySelectorAll('.qjESne, .THOPZb, .VfPpkd-rymPhb-ibnC6b, [role="button"], .fontBodyMedium');
                            console.log(`Found ${fallbackCards.length} fallback cards`);
                            
                            fallbackCards.forEach((card, index) => {
                                try {
                                    const nameSelectors = ['h3', '.fontHeadlineSmall', '.qBF1Pd', '.NrDZNb', '.fontHeadlineMedium', '.fontBodyLarge'];
                                    let name = '';
                                    for (const selector of nameSelectors) {
                                        const nameEl = card.querySelector(selector);
                                        if (nameEl && nameEl.innerText.trim()) {
                                            name = nameEl.innerText.trim();
                                            break;
                                        }
                                    }
                                    
                                    if (name && name.length > 2 && !processedNames.has(name)) {
                                        processedNames.add(name);
                                        
                                        const allText = card.innerText;
                                        const phoneRegex = /(?:\\+92|0)?\\s?3\\d{2}\\s?\\d{7}|(?:\\+92|0)?\\s?\\d{2,4}\\s?\\d{7,8}/g;
                                        const phoneMatches = allText.match(phoneRegex);
                                        const phone = phoneMatches ? phoneMatches[0].trim() : '';
                                        
                                        businesses.push({
                                            name: name,
                                            rating: '',
                                            reviewCount: '',
                                            phone: phone,
                                            category: 'Car Rental Agency',
                                            address: '',
                                            rawText: allText,
                                            elementIndex: businesses.length + index
                                        });
                                        console.log(`Fallback: Added business "${name}"`);
                                    }
                                } catch (error) {
                                    console.log(`Error in fallback extraction ${index}:`, error);
                                }
                            });
                        }
                        
                        return businesses;
                    }
                ''')
                
                logger.info(f"Extracted {len(businesses_data)} unique businesses from page")
                
                # Process each business to get website by clicking
                final_businesses = []
                processed_count = 0
                
                for business_data in businesses_data[:max_results]:
                    try:
                        # Find the business element again
                        business_elements = page.query_selector_all('[data-result-index], .Nv2PK, .lI9IFe, .bfdHYd')
                        
                        if business_data['elementIndex'] < len(business_elements):
                            element = business_elements[business_data['elementIndex']]
                            
                            # Click to open details panel
                            try:
                                element.click()
                                page.wait_for_timeout(2000)  # Wait for details to load
                                
                                # Extract website from details panel
                                website = page.evaluate('''
                                    () => {
                                        // Look for website link in details panel
                                        const websiteSelectors = [
                                            'a[data-item-id="authority"]',
                                            'a[href*="http"]:not([href*="google.com"]):not([href*="maps"])',
                                            '[data-item-id="authority"] a',
                                            '.CsEnBe a[href^="http"]:not([href*="google"])'
                                        ];
                                        
                                        for (const selector of websiteSelectors) {
                                            const link = document.querySelector(selector);
                                            if (link && link.href && !link.href.includes('google.com') && !link.href.includes('maps')) {
                                                return link.href;
                                            }
                                        }
                                        return '';
                                    }
                                ''')
                                
                                # Extract social media and email from details panel
                                social_data = page.evaluate('''
                                    () => {
                                        const socialData = {
                                            email: '',
                                            facebook: '',
                                            instagram: '',
                                            twitter: '',
                                            linkedin: '',
                                            youtube: '',
                                            whatsapp: ''
                                        };
                                        
                                        // Strategy 1: Look for email in contact info
                                        const emailSelectors = [
                                            'a[href^="mailto:"]',
                                            '[data-item-id="email"]',
                                            '.Io6YTe.fontBodyMedium[href^="mailto:"]',
                                            '.rogA2c a[href^="mailto:"]'
                                        ];
                                        
                                        for (const selector of emailSelectors) {
                                            const emailEl = document.querySelector(selector);
                                            if (emailEl && emailEl.href) {
                                                const email = emailEl.href.replace('mailto:', '');
                                                if (email.includes('@')) {
                                                    socialData.email = email;
                                                    break;
                                                }
                                            }
                                        }
                                        
                                        // Strategy 2: Look for social media links
                                        const allLinks = document.querySelectorAll('a[href]');
                                        for (const link of allLinks) {
                                            const href = link.href.toLowerCase();
                                            const text = link.innerText.toLowerCase();
                                            
                                            // Facebook
                                            if (href.includes('facebook.com') || text.includes('facebook')) {
                                                socialData.facebook = link.href;
                                            }
                                            // Instagram
                                            else if (href.includes('instagram.com') || text.includes('instagram')) {
                                                socialData.instagram = link.href;
                                            }
                                            // Twitter/X
                                            else if (href.includes('twitter.com') || href.includes('x.com') || text.includes('twitter')) {
                                                socialData.twitter = link.href;
                                            }
                                            // LinkedIn
                                            else if (href.includes('linkedin.com') || text.includes('linkedin')) {
                                                socialData.linkedin = link.href;
                                            }
                                            // YouTube
                                            else if (href.includes('youtube.com') || text.includes('youtube')) {
                                                socialData.youtube = link.href;
                                            }
                                            // WhatsApp
                                            else if (href.includes('wa.me') || href.includes('whatsapp.com') || text.includes('whatsapp')) {
                                                socialData.whatsapp = link.href;
                                            }
                                        }
                                        
                                        // Strategy 3: Look for email in text content
                                        if (!socialData.email) {
                                            const allText = document.body.innerText;
                                            const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}/g;
                                            const emailMatches = allText.match(emailRegex);
                                            if (emailMatches && emailMatches.length > 0) {
                                                const validEmails = emailMatches.filter(email => 
                                                    !email.includes('google.com') && 
                                                    !email.includes('example.com') &&
                                                    email.length > 5
                                                );
                                                if (validEmails.length > 0) {
                                                    socialData.email = validEmails[0];
                                                }
                                            }
                                        }
                                        
                                        return socialData;
                                    }
                                ''')
                                
                                # Enhanced address extraction from details panel
                                enhanced_address = page.evaluate('''
                                    () => {
                                        const addressSelectors = [
                                            '[data-item-id="address"]',
                                            '.Io6YTe.fontBodyMedium:not(.Liguzb)',
                                            '.rogA2c .fontBodyMedium'
                                        ];
                                        
                                        for (const selector of addressSelectors) {
                                            const addrEl = document.querySelector(selector);
                                            if (addrEl && addrEl.innerText && !addrEl.innerText.includes('hour') && !addrEl.innerText.includes('star')) {
                                                return addrEl.innerText.trim();
                                            }
                                        }
                                        return '';
                                    }
                                ''')
                                
                            except Exception as click_error:
                                logger.warning(f"Could not click business {business_data['name']}: {click_error}")
                                website = ''
                                enhanced_address = business_data['address']
                                social_data = {'email': '', 'facebook': '', 'instagram': '', 'twitter': '', 'linkedin': '', 'youtube': '', 'whatsapp': ''}
                        else:
                            website = ''
                            enhanced_address = business_data['address']
                            social_data = {'email': '', 'facebook': '', 'instagram': '', 'twitter': '', 'linkedin': '', 'youtube': '', 'whatsapp': ''}
                        
                        # Try website-based social media extraction if we have a website
                        # REMOVED: Social media extraction moved to secondary server
                        # if website and website != '':
                        #     try:
                        #         website_social = self.extract_social_from_website(website, business_data['name'])
                        #         # Merge with existing social data (prioritize Google Maps data)
                        #         for key in social_data:
                        #             if not social_data[key] and website_social.get(key):
                        #                 social_data[key] = website_social[key]
                        #     except Exception as e:
                        #         logger.warning(f"Error extracting social from website {website}: {e}")
                        
                        # Clean social media URLs and emails
                        cleaned_social = {}
                        for platform, url in social_data.items():
                            if platform == 'email':
                                cleaned_social[platform] = self.data_extractor.clean_email(url)
                            else:
                                cleaned_social[platform] = self.data_extractor.clean_social_url(url)
                        
                        # Clean and validate data
                        cleaned_business = {
                            'name': business_data['name'],
                            'rating': self.clean_rating(business_data['rating']),
                            'review_count': self.clean_review_count(business_data['reviewCount']),
                            'address': enhanced_address or business_data['address'],
                            'category': self.clean_category(business_data['category']),
                            'phone': self.clean_phone(business_data['phone']),
                            'website': self.clean_website(website),
                            'email': '',  # Will be filled by secondary server
                            'facebook': '',  # Will be filled by secondary server
                            'instagram': '',  # Will be filled by secondary server
                            'twitter': '',  # Will be filled by secondary server
                            'linkedin': '',  # Will be filled by secondary server
                            'youtube': '',  # Will be filled by secondary server
                            'whatsapp': '',  # Will be filled by secondary server
                            'search_term': search_term,
                            'area': area_name,
                            'coordinates': f"{latitude},{longitude}",
                            'scraped_date': datetime.now().strftime('%Y-%m-%d')
                        }
                        
                        # Quality filter
                        if self.is_valid_business(cleaned_business):
                            final_businesses.append(cleaned_business)
                            processed_count += 1
                            logger.info(f"Processed {processed_count}/{len(businesses_data)}: {cleaned_business['name']}")
                    
                    except Exception as e:
                        logger.warning(f"Error processing business {business_data.get('name', 'unknown')}: {e}")
                        continue
                
                browser.close()
                
                # Final deduplication
                unique_businesses = self.deduplicate_businesses(final_businesses)
                
                logger.info(f"Final result: {len(unique_businesses)} unique businesses")
                
                return {
                    "businesses": unique_businesses,
                    "total_found": len(unique_businesses),
                    "search_term": search_term,
                    "area": area_name,
                    "coordinates": f"{latitude},{longitude}",
                    "scraped_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error in Playwright scraping: {str(e)}")
            return {"businesses": [], "error": str(e)}
    
    def clean_rating(self, rating):
        """Clean rating data"""
        if not rating:
            return ""
        # Extract just the number
        import re
        match = re.search(r'(\d+\.?\d*)', rating)
        return match.group(1) if match else ""
    
    def clean_review_count(self, review_count):
        """Clean review count data"""
        if not review_count:
            return ""
        # Extract number from parentheses or just number
        import re
        match = re.search(r'\(?(\d+(?:,\d+)?)\)?', review_count)
        return match.group(1) if match else ""
    
    def clean_category(self, category):
        """Clean category data"""
        if not category:
            return "Car Rental Agency"
        # Remove address-like content from category
        lines = category.split('·')
        return lines[0].strip() if lines else category.strip()
    
    def clean_phone(self, phone):
        """Clean phone data"""
        if not phone:
            return ""
        # Remove extra characters, keep just the phone
        import re
        match = re.search(r'(\+?92\s?\d{3}\s?\d{7}|\d{4}\s?\d{7})', phone)
        return match.group(1).strip() if match else phone.strip()
    
    def clean_website(self, website):
        """Clean and validate website URL"""
        if not website:
            return ""
        
        # Remove common invalid websites
        invalid_domains = ['google.com', 'maps.google.com', 'facebook.com', 'instagram.com']
        website_lower = website.lower()
        
        for domain in invalid_domains:
            if domain in website_lower:
                return ""
        
        # Ensure it's a proper URL
        if not website.startswith('http'):
            website = 'https://' + website
        
        # Remove trailing slashes
        website = website.rstrip('/')
        
        return website

    def extract_social_from_website(self, website_url, business_name):
        """Extract social media and email from business website"""
        if not website_url or 'google.com' in website_url or 'facebook.com' in website_url:
            return {'email': '', 'facebook': '', 'instagram': '', 'twitter': '', 'linkedin': '', 'youtube': '', 'whatsapp': ''}
        
        social_data = {
            'email': '',
            'facebook': '',
            'instagram': '',
            'twitter': '',
            'linkedin': '',
            'youtube': '',
            'whatsapp': ''
        }
        
        try:
            import requests
            from bs4 import BeautifulSoup
            import re
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Try main page first
            response = requests.get(website_url, headers=headers, timeout=15, allow_redirects=True)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract email with better regex
            email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            page_text = soup.get_text()
            emails = re.findall(email_regex, page_text)
            
            # Filter out common invalid emails
            valid_emails = []
            for email in emails:
                email_lower = email.lower()
                if (not email_lower.endswith('@example.com') and 
                    not email_lower.endswith('@test.com') and
                    not email_lower.endswith('@google.com') and
                    '@' in email and
                    len(email) > 5):
                    valid_emails.append(email)
            
            if valid_emails:
                social_data['email'] = valid_emails[0]
            
            # Extract social media links with better selectors
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href', '').lower()
                text = link.get_text().lower()
                
                # Facebook - check for various patterns
                if ('facebook.com' in href or 
                    'fb.com' in href or 
                    'facebook' in text or
                    'fb' in text):
                    if not social_data['facebook']:  # Only take first match
                        social_data['facebook'] = link['href']
                
                # Instagram
                elif ('instagram.com' in href or 
                      'ig.com' in href or 
                      'instagram' in text):
                    if not social_data['instagram']:
                        social_data['instagram'] = link['href']
                
                # Twitter/X
                elif ('twitter.com' in href or 
                      'x.com' in href or 
                      'twitter' in text):
                    if not social_data['twitter']:
                        social_data['twitter'] = link['href']
                
                # LinkedIn
                elif ('linkedin.com' in href or 
                      'linkedin' in text):
                    if not social_data['linkedin']:
                        social_data['linkedin'] = link['href']
                
                # YouTube
                elif ('youtube.com' in href or 
                      'youtube' in text or
                      'youtu.be' in href):
                    if not social_data['youtube']:
                        social_data['youtube'] = link['href']
                
                # WhatsApp
                elif ('wa.me' in href or 
                      'whatsapp.com' in href or 
                      'whatsapp' in text):
                    if not social_data['whatsapp']:
                        social_data['whatsapp'] = link['href']
            
            # Try contact page if no social media found
            if not any([social_data['email'], social_data['facebook'], social_data['instagram'], 
                       social_data['twitter'], social_data['linkedin'], social_data['youtube'], social_data['whatsapp']]):
                
                # Look for contact page links
                contact_links = []
                for link in all_links:
                    href = link.get('href', '').lower()
                    text = link.get_text().lower()
                    if any(word in href or word in text for word in ['contact', 'about', 'info']):
                        contact_links.append(link['href'])
                
                # Try each contact page
                for contact_link in contact_links[:3]:  # Limit to 3 attempts
                    try:
                        if not contact_link.startswith('http'):
                            if contact_link.startswith('/'):
                                contact_url = website_url.rstrip('/') + contact_link
                            else:
                                contact_url = website_url.rstrip('/') + '/' + contact_link
                        else:
                            contact_url = contact_link
                        
                        contact_response = requests.get(contact_url, headers=headers, timeout=10)
                        contact_soup = BeautifulSoup(contact_response.text, 'html.parser')
                        
                        # Extract emails from contact page
                        contact_text = contact_soup.get_text()
                        contact_emails = re.findall(email_regex, contact_text)
                        for email in contact_emails:
                            email_lower = email.lower()
                            if (not email_lower.endswith('@example.com') and 
                                not email_lower.endswith('@test.com') and
                                '@' in email):
                                social_data['email'] = email
                                break
                        
                        # Extract social media from contact page
                        contact_links = contact_soup.find_all('a', href=True)
                        for link in contact_links:
                            href = link.get('href', '').lower()
                            text = link.get_text().lower()
                            
                            if ('facebook.com' in href or 'fb.com' in href) and not social_data['facebook']:
                                social_data['facebook'] = link['href']
                            elif ('instagram.com' in href or 'ig.com' in href) and not social_data['instagram']:
                                social_data['instagram'] = link['href']
                            elif ('twitter.com' in href or 'x.com' in href) and not social_data['twitter']:
                                social_data['twitter'] = link['href']
                            elif 'linkedin.com' in href and not social_data['linkedin']:
                                social_data['linkedin'] = link['href']
                            elif ('youtube.com' in href or 'youtu.be' in href) and not social_data['youtube']:
                                social_data['youtube'] = link['href']
                            elif ('wa.me' in href or 'whatsapp.com' in href) and not social_data['whatsapp']:
                                social_data['whatsapp'] = link['href']
                        
                        # If we found something, break
                        if any(social_data.values()):
                            break
                            
                    except Exception as e:
                        logger.debug(f"Error accessing contact page {contact_link}: {e}")
                        continue
                            
        except Exception as e:
            logger.warning(f"Error extracting social from {website_url}: {e}")
        
        return social_data

    def is_valid_business(self, business):
        """Check if business has minimum required data"""
        return (business['name'] and 
                len(business['name']) > 2 and
                (business['address'] or business['phone']))
    
    def deduplicate_businesses(self, businesses):
        """Remove duplicate businesses using fuzzy matching"""
        if not businesses:
            return businesses
            
        unique_businesses = []
        seen_names = set()
        
        for business in businesses:
            name_lower = business['name'].lower().strip()
            
            # Simple exact match first
            if name_lower in seen_names:
                continue
                
            # Check for fuzzy duplicates
            is_duplicate = False
            for existing_name in seen_names:
                if self.data_extractor.is_similar_text(name_lower, existing_name, threshold=0.85):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                seen_names.add(name_lower)
                unique_businesses.append(business)
        
        return unique_businesses
    
    def enhanced_scroll_results(self, max_results):
        """Enhanced scrolling with multiple strategies"""
        try:
            # Find results panel with multiple strategies
            results_panel = None
            panel_selectors = ["[role='main']", ".m6QErb", ".siAUzd", ".TFQHme", "#pane"]
            
            for selector in panel_selectors:
                try:
                    results_panel = self.driver.find_element(By.CSS_SELECTOR, selector)
                    logger.debug(f"Found results panel with selector: {selector}")
                    break
                except NoSuchElementException:
                    continue
            
            if not results_panel:
                logger.warning("Could not find results panel for scrolling")
                return 0
            
            last_count = 0
            no_change_count = 0
            best_count = 0
            
            # Multiple element selectors for comprehensive detection
            element_selectors = [
                "[data-result-index]", ".Nv2PK", ".lI9IFe", ".bfdHYd", 
                ".qjESne", ".THOPZb", ".VfPpkd-rymPhb-ibnC6b", ".fontHeadlineSmall"
            ]
            
            for i in range(self.settings["scroll_attempts"]):
                # Get current business count with multiple selectors
                current_businesses = 0
                for selector in element_selectors:
                    count = len(self.driver.find_elements(By.CSS_SELECTOR, selector))
                    current_businesses = max(current_businesses, count)
                
                logger.debug(f"Scroll {i+1}: Found {current_businesses} businesses")
                best_count = max(best_count, current_businesses)
                
                if current_businesses >= max_results:
                    logger.info(f"Reached target of {max_results} businesses")
                    break
                
                # Check progress
                if current_businesses == last_count:
                    no_change_count += 1
                else:
                    no_change_count = 0
                    last_count = current_businesses
                
                # Progressive scrolling strategies
                if no_change_count >= 3:
                    logger.debug("No progress, trying alternative scrolling methods")
                    
                    # Strategy 1: Scroll entire page
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)
                    
                    # Strategy 2: Scroll multiple containers
                    for container_sel in panel_selectors:
                        try:
                            container = self.driver.find_element(By.CSS_SELECTOR, container_sel)
                            for scroll_amount in [500, 1000, 1500]:
                                self.driver.execute_script(f"arguments[0].scrollTop += {scroll_amount}", container)
                                time.sleep(0.5)
                        except:
                            continue
                    
                    # Strategy 3: JavaScript-based scrolling
                    self.driver.execute_script("""
                        var elements = document.querySelectorAll('[role="main"], .m6QErb, .siAUzd');
                        elements.forEach(function(el) {
                            el.scrollTop = el.scrollHeight;
                        });
                    """)
                    time.sleep(1)
                    
                    # Check if alternative methods helped
                    new_count = 0
                    for selector in element_selectors:
                        count = len(self.driver.find_elements(By.CSS_SELECTOR, selector))
                        new_count = max(new_count, count)
                    
                    if new_count > current_businesses:
                        logger.debug(f"Alternative scrolling worked: {new_count} businesses")
                        no_change_count = 0
                        last_count = new_count
                        best_count = max(best_count, new_count)
                    elif no_change_count >= 6:
                        logger.info(f"No more results after {i+1} scrolls, stopping")
                        break
                
                # Regular scrolling with micro-scrolls
                self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", results_panel)
                time.sleep(self.settings["scroll_delay"])
                
                # Micro-scrolling for stubborn content
                for micro in range(2):
                    self.driver.execute_script("arguments[0].scrollTop += 400", results_panel)
                    time.sleep(0.3)
                
                # Simulate user behavior
                if i % 3 == 0:
                    self.driver.execute_script("window.scrollTo(0, 100);")
                    time.sleep(0.5)
                    self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", results_panel)
            
            final_count = best_count
            logger.info(f"Enhanced scrolling completed. Final count: {final_count} businesses")
            return final_count
                        
        except Exception as e:
            logger.warning(f"Error during enhanced scrolling: {e}")
            return 0
    
    def advanced_extract_business_data(self, search_term, area_name, latitude, longitude):
        """Advanced business data extraction with multiple strategies"""
        businesses = []
        
        # Comprehensive element selectors
        selectors = [
            "[data-result-index]", ".Nv2PK", ".lI9IFe", ".bfdHYd", 
            ".qjESne", ".THOPZb", ".VfPpkd-rymPhb-ibnC6b"
        ]
        
        all_elements = []
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logger.info(f"Found {len(elements)} businesses using selector: {selector}")
                    all_elements.extend(elements)
            except Exception as e:
                logger.warning(f"Error with selector {selector}: {e}")
                continue
        
        # Remove duplicates based on position and text
        unique_elements = self.deduplicate_elements(all_elements)
        logger.info(f"After deduplication: {len(unique_elements)} unique business elements")
        
        if not unique_elements:
            logger.warning("No business elements found with any selector")
            return []
        
        # Process each business element with advanced extraction
        for i, element in enumerate(unique_elements[:50]):  # Process up to 50
            try:
                # Get comprehensive element data
                element_html = element.get_attribute('outerHTML')
                element_text = self.safe_get_text(element)
                
                if not element_text or len(element_text.strip()) < 5:
                    continue
                
                # Advanced extraction
                business = self.advanced_extract_single_business(
                    element, element_text, element_html, search_term, area_name, latitude, longitude
                )
                
                if business and business.get('name') and len(business['name']) > 2:
                    # Avoid duplicates
                    if not self.is_duplicate_business(business, businesses):
                        businesses.append(business)
                        logger.info(f"Extracted: {business['name']} | Phone: {business['phone']} | Address: {business['address'][:50]}...")
                
                # Controlled delay
                time.sleep(self.settings["extraction_delay"])
                
            except Exception as e:
                logger.warning(f"Error extracting business {i}: {e}")
                continue
        
        return businesses
    
    def deduplicate_elements(self, elements):
        """Remove duplicate elements based on position and content"""
        unique_elements = []
        seen_positions = set()
        seen_texts = set()
        
        for element in elements:
            try:
                # Get element position and text
                location = element.location
                text = self.safe_get_text(element)
                
                position_key = f"{location['x']},{location['y']}"
                text_key = text[:100].lower().strip()
                
                if position_key not in seen_positions and text_key not in seen_texts and len(text) > 10:
                    unique_elements.append(element)
                    seen_positions.add(position_key)
                    seen_texts.add(text_key)
                    
            except Exception:
                continue
        
        return unique_elements
    
    def is_duplicate_business(self, business, existing_businesses):
        """Check if business is duplicate using fuzzy matching"""
        for existing in existing_businesses:
            # Check name similarity
            name_similarity = fuzz.ratio(business['name'].lower(), existing['name'].lower())
            if name_similarity > 85:
                return True
            
            # Check phone similarity
            if business['phone'] and existing['phone']:
                phone_similarity = fuzz.ratio(business['phone'], existing['phone'])
                if phone_similarity > 90:
                    return True
        
        return False
    
    def advanced_extract_single_business(self, element, element_text, element_html, search_term, area_name, latitude, longitude):
        """Advanced single business extraction with ML-like classification"""
        business = {
            'name': '',
            'rating': '',
            'review_count': '',
            'address': '',
            'category': '',
            'phone': '',
            'website': '',
            'search_term': search_term,
            'area': area_name,
            'coordinates': f"{latitude},{longitude}",
            'scraped_date': datetime.now().strftime('%Y-%m-%d')
        }
        
        try:
            # Parse HTML with BeautifulSoup for better extraction
            soup = BeautifulSoup(element_html, 'html.parser')
            
            # Extract from visible text with advanced classification
            lines = [line.strip() for line in element_text.split('\n') if line.strip()]
            
            # --- Extract Name (first meaningful line) ---
            if lines:
                business['name'] = lines[0][:100]
            
            # --- Extract Rating and Reviews with better patterns ---
            for line in lines:
                # Rating pattern
                rating_match = re.search(r'(\d+\.?\d*)\s*(?:stars?|★|⭐)?', line)
                if rating_match and not business['rating']:
                    rating_val = float(rating_match.group(1))
                    if 1.0 <= rating_val <= 5.0:
                        business['rating'] = rating_match.group(1)
                
                # Review count with better patterns
                review_patterns = [
                    r'\((\d{1,6})\)',  # (452)
                    r'(\d{1,6})\s*reviews?',  # 452 reviews
                    r'(\d{1,6})\s*ratings?'   # 452 ratings
                ]
                
                for pattern in review_patterns:
                    review_match = re.search(pattern, line.replace(',', ''), re.I)
                    if review_match and not business['review_count']:
                        business['review_count'] = review_match.group(1)
                        break
            
            # --- Advanced Phone Extraction ---
            phones = self.data_extractor.extract_phone_numbers(element_text)
            if phones:
                business['phone'] = phones[0]  # Take the first/best match
            
            # --- Advanced Website Extraction ---
            websites = self.data_extractor.extract_websites(element_text)
            if websites:
                business['website'] = websites[0]
            
            # --- Enhanced Address Extraction ---
            address_candidates = []
            category_candidates = []
            debug_lines = []
            # 1. Try DOM selectors with BeautifulSoup
            address_selectors = [
                '[data-value="Address"]', '.LrzXr', '.W4Efsd:last-child', '[aria-label*="address"]',
                '.rogA2c', '.rllt__details', '.W4Efsd[data-value="Address"]'
            ]
            for selector in address_selectors:
                for tag in soup.select(selector):
                    addr_text = tag.get_text(strip=True)
                    if addr_text and not self.data_extractor.is_review_line(addr_text):
                        address_candidates.append(addr_text)
                        debug_lines.append(f"DOM address: {addr_text}")
            # 2. Try visible text lines
            for line in lines[1:]:
                if self.data_extractor.is_review_line(line):
                    debug_lines.append(f"Filtered review: {line}")
                    continue
                classification = self.data_extractor.classify_text_line(line, business['name'])
                debug_lines.append(f"{classification}: {line}")
                if classification == 'address':
                    address_candidates.append(line)
                elif classification == 'category':
                    category_candidates.append(line)
            # 3. Pick best address
            if address_candidates:
                best_address = max(address_candidates, key=len)
                business['address'] = self.data_extractor.clean_address(best_address, business['name'])
            # 4. Enhanced category extraction
            category_selectors = ['.DkEaL', '.W4Efsd:first-child', '.YhemCb']
            for selector in category_selectors:
                for tag in soup.select(selector):
                    cat_text = tag.get_text(strip=True)
                    if cat_text and not self.data_extractor.is_review_line(cat_text):
                        category_candidates.append(cat_text)
                        debug_lines.append(f"DOM category: {cat_text}")
            if category_candidates:
                best_category = category_candidates[0]
                business['category'] = self.data_extractor.clean_category(best_category, business['name'])
            else:
                business['category'] = 'Car Rental Agency'
            # Debug log for first 3 businesses
            if i < 3:
                logger.debug(f"[DEBUG] Address/category candidates for {business['name']}:\n" + '\n'.join(debug_lines))
            
            # --- Enhanced DOM-based extraction as fallback ---
            if not business['website']:
                # Try to find website links in DOM
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '')
                    if href and 'http' in href and 'google.com' not in href and 'maps' not in href:
                        business['website'] = href
                        break
            
            if not business['phone']:
                # Try to find phone in DOM attributes or text
                phone_elements = soup.find_all(text=re.compile(r'\d{3,4}[\s\-]?\d{7}'))
                for phone_text in phone_elements:
                    phones = self.data_extractor.extract_phone_numbers(phone_text)
                    if phones:
                        business['phone'] = phones[0]
                        break
            
            # --- Final data cleaning and validation ---
            if business['name']:
                business['name'] = re.sub(r'\s+', ' ', business['name']).strip()
            
            if business['address']:
                business['address'] = re.sub(r'\s+', ' ', business['address']).strip()
                # Final check - don't use business name as address
                if self.data_extractor.is_similar_text(business['address'].lower(), business['name'].lower(), threshold=0.8):
                    business['address'] = ''
            
            if business['category']:
                business['category'] = re.sub(r'\s+', ' ', business['category']).strip()
            
            if business['phone']:
                business['phone'] = re.sub(r'[^\d\+\-\s\(\)]', '', business['phone']).strip()
            
            # Quality score (for potential filtering)
            quality_score = 0
            if business['name']: quality_score += 1
            if business['phone']: quality_score += 1
            if business['address']: quality_score += 1
            if business['website']: quality_score += 1
            if business['rating']: quality_score += 1
            
            # Only return businesses with decent quality
            if quality_score >= 2:
                return business
            
        except Exception as e:
            logger.warning(f"Error in advanced extraction: {e}")
        
        return None
    
    def close(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
            logger.info("Driver closed")

    def enrich_with_contact_details(self, businesses):
        """Enrich businesses with contact details using secondary server"""
        if not businesses:
            return businesses
        
        try:
            # Send businesses to contact details server
            response = requests.post(
                'http://127.0.0.1:5001/enrich',
                json={'businesses': businesses},
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    logger.info(f"Successfully enriched {result.get('total_enriched', 0)} businesses with contact details")
                    return result.get('businesses', businesses)
                else:
                    logger.warning("Contact details server returned error")
            else:
                logger.warning(f"Contact details server returned status {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            logger.warning("Contact details server not available, returning businesses without enrichment")
        except Exception as e:
            logger.error(f"Error enriching with contact details: {e}")
        
        return businesses

# Global scraper instance
scraper = GoogleMapsScraper()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/scrape', methods=['POST'])
def scrape_endpoint():
    """Scrape businesses from Google Maps"""
    try:
        data = request.get_json()
        
        # Extract parameters
        search_term = data.get('search_term', '')
        area_name = data.get('area_name', '')
        latitude = data.get('latitude', 0.0)
        longitude = data.get('longitude', 0.0)
        radius_km = data.get('radius_km', 5)
        max_results = data.get('max_results', 30)
        
        if not search_term or not area_name:
            return jsonify({"error": "search_term and area_name are required"}), 400
        
        logger.info(f"Received scraping request: {search_term} in {area_name}")
        
        # Perform scraping
        result = scraper.scrape_businesses(
            search_term=search_term,
            area_name=area_name,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            max_results=max_results
        )
        
        if "error" in result:
            return jsonify({"error": result["error"]}), 500
        
        # Enrich with contact details
        if result.get("businesses"):
            enriched_businesses = scraper.enrich_with_contact_details(result["businesses"])
            result["businesses"] = enriched_businesses
            result["total_found"] = len(enriched_businesses)
        
        return jsonify({
            "success": True,
            "data": result,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in scrape endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/scrape-batch', methods=['POST'])
def scrape_batch_endpoint():
    """Batch scraping endpoint for multiple locations"""
    try:
        data = request.get_json()
        locations = data.get('locations', [])
        
        if not locations:
            return jsonify({"error": "No locations provided"}), 400
        
        results = []
        
        for location in locations:
            try:
                # Validate location data
                required_fields = ['search_term', 'area_name', 'latitude', 'longitude']
                if not all(field in location for field in required_fields):
                    results.append({
                        "location": location.get('area_name', 'Unknown'),
                        "success": False,
                        "error": "Missing required fields"
                    })
                    continue
                
                # Scrape this location
                result = scraper.scrape_businesses(
                    search_term=location['search_term'],
                    area_name=location['area_name'],
                    latitude=float(location['latitude']),
                    longitude=float(location['longitude']),
                    radius_km=int(location.get('radius_km', 5)),
                    max_results=int(location.get('max_results', 30))
                )
                
                results.append({
                    "location": location['area_name'],
                    "success": True,
                    "data": result
                })
                
                # Small delay between locations
                time.sleep(3)
                
            except Exception as e:
                logger.error(f"Error scraping {location.get('area_name', 'Unknown')}: {str(e)}")
                results.append({
                    "location": location.get('area_name', 'Unknown'),
                    "success": False,
                    "error": str(e)
                })
        
        return jsonify({
            "success": True,
            "results": results,
            "total_locations": len(locations),
            "successful_scrapes": len([r for r in results if r['success']]),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in batch scrape endpoint: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/restart-driver', methods=['POST'])
def restart_driver():
    """Restart the Chrome driver (useful if it gets stuck)"""
    try:
        scraper.close()
        time.sleep(2)
        scraper.start_driver()
        return jsonify({"success": True, "message": "Driver restarted"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    logger.info("Starting Google Maps Scraper API Server...")
    logger.info("Available endpoints:")
    logger.info("  GET  /health - Health check")
    logger.info("  POST /scrape - Scrape single location")
    logger.info("  POST /scrape-batch - Scrape multiple locations")
    logger.info("  POST /restart-driver - Restart Chrome driver")
    
    # Start the Flask server
    app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)
#!/usr/bin/env python3
"""
Contact Details Server - Secondary Server for Intelligent Contact Extraction
Handles website scraping, social media validation, and contact detail enrichment
"""

import os
import sys
import json
import time
import logging
import requests
import threading
from datetime import datetime
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
import concurrent.futures
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class ContactDetailsExtractor:
    """Intelligent contact details extraction from business websites"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Invalid domains to skip
        self.invalid_domains = {
            'google.com', 'maps.google.com', 'facebook.com', 'instagram.com',
            'twitter.com', 'linkedin.com', 'youtube.com', 'example.com',
            'test.com', 'localhost', '127.0.0.1'
        }
        
        # Social media patterns
        self.social_patterns = {
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
                r'wa\.me/[\w\.-]+',
                r'whatsapp\.com/send\?phone=[\w\.-]+'
            ]
        }
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and not in invalid domains"""
        if not url or not url.startswith('http'):
            return False
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            return not any(invalid in domain for invalid in self.invalid_domains)
        except:
            return False
    
    def extract_emails(self, text: str) -> List[str]:
        """Extract valid emails from text with enhanced patterns"""
        # Multiple email regex patterns for better coverage
        email_patterns = [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        ]
        
        emails = []
        for pattern in email_patterns:
            found_emails = re.findall(pattern, text)
            emails.extend(found_emails)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_emails = []
        for email in emails:
            email_lower = email.lower()
            if email_lower not in seen:
                seen.add(email_lower)
                unique_emails.append(email)
        
        # Enhanced filtering for valid emails
        valid_emails = []
        invalid_domains = {
            'example.com', 'test.com', 'google.com', 'gmail.com', 
            'yahoo.com', 'hotmail.com', 'outlook.com', 'live.com',
            'domain.com', 'sample.com', 'demo.com', 'placeholder.com'
        }
        
        for email in unique_emails:
            email_lower = email.lower()
            
            # Skip if it's a common personal email domain
            domain = email_lower.split('@')[-1] if '@' in email_lower else ''
            
            if (not any(invalid in email_lower for invalid in ['@example.com', '@test.com', '@google.com']) and
                '@' in email and len(email) > 5 and
                domain not in invalid_domains and
                not email_lower.startswith('admin@') and
                not email_lower.startswith('test@') and
                not email_lower.startswith('info@example') and
                not email_lower.startswith('contact@example')):
                valid_emails.append(email)
        
        return valid_emails
    
    def extract_social_media(self, soup: BeautifulSoup, base_url: str) -> Dict[str, str]:
        """Extract social media links from BeautifulSoup object"""
        social_data = {
            'facebook': '', 'instagram': '', 'twitter': '', 
            'linkedin': '', 'youtube': '', 'whatsapp': ''
        }
        
        # Find all links
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '').lower()
            text = link.get_text().lower()
            
            # Facebook
            if ('facebook.com' in href or 'fb.com' in href) and not social_data['facebook']:
                if self.is_valid_social_url(href, 'facebook'):
                    social_data['facebook'] = self.clean_social_url(href, base_url)
            
            # Instagram
            elif ('instagram.com' in href or 'ig.com' in href) and not social_data['instagram']:
                if self.is_valid_social_url(href, 'instagram'):
                    social_data['instagram'] = self.clean_social_url(href, base_url)
            
            # Twitter/X
            elif ('twitter.com' in href or 'x.com' in href) and not social_data['twitter']:
                if self.is_valid_social_url(href, 'twitter'):
                    social_data['twitter'] = self.clean_social_url(href, base_url)
            
            # LinkedIn
            elif 'linkedin.com' in href and not social_data['linkedin']:
                if self.is_valid_social_url(href, 'linkedin'):
                    social_data['linkedin'] = self.clean_social_url(href, base_url)
            
            # YouTube
            elif ('youtube.com' in href or 'youtu.be' in href) and not social_data['youtube']:
                if self.is_valid_social_url(href, 'youtube'):
                    social_data['youtube'] = self.clean_social_url(href, base_url)
            
            # WhatsApp
            elif ('wa.me' in href or 'whatsapp.com' in href) and not social_data['whatsapp']:
                if self.is_valid_social_url(href, 'whatsapp'):
                    social_data['whatsapp'] = self.clean_social_url(href, base_url)
        
        return social_data
    
    def is_valid_social_url(self, url: str, platform: str) -> bool:
        """Validate if social media URL is legitimate"""
        if not url or not url.startswith('http'):
            return False
        
        # Check for generic/placeholder URLs
        generic_patterns = [
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/?$',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/$',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/[\s]*$',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/share/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/profile\.php\?id=',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/pages/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/groups/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/events/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/help/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/about/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/privacy/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/terms/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/contact/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/support/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/login',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/signup',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/forgot-password',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/security',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/settings',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/ads/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/business/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/developers/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/careers/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/press/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/investors/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/legal/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/cookies/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/accessibility/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/community/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/developers/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/partners/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/creators/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/gaming/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/watch/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/videos/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/live/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/trending/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/subscriptions/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/playlist/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/channel/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/user/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/c/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/@',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/u/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/i/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/t/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/s/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/o/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/p/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/m/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/w/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/x/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/y/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/z/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/0/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/1/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/2/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/3/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/4/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/5/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/6/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/7/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/8/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/9/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/a/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/b/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/c/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/d/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/e/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/f/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/g/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/h/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/i/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/j/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/k/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/l/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/m/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/n/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/o/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/p/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/q/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/r/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/s/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/t/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/u/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/v/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/w/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/x/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/y/',
            r'https?://(www\.)?(facebook|instagram|twitter|linkedin|youtube)\.com/z/'
        ]
        
        for pattern in generic_patterns:
            if re.match(pattern, url):
                return False
        
        # Check for minimum length (should have username/ID)
        if len(url) < 30:  # Increased from 25 for better validation
            return False
        
        # Check for specific business indicators in URL
        business_indicators = [
            'company', 'business', 'official', 'page', 'profile',
            'rent', 'car', 'tours', 'travel', 'service', 'agency',
            'rental', 'transport', 'cab', 'taxi', 'drive', 'auto'
        ]
        
        url_lower = url.lower()
        has_business_indicator = any(indicator in url_lower for indicator in business_indicators)
        
        # If URL is too short or doesn't have business indicators, be more strict
        if len(url) < 40 and not has_business_indicator:
            return False
        
        return True
    
    def clean_social_url(self, url: str, base_url: str) -> str:
        """Clean and normalize social media URL"""
        if not url:
            return ""
        
        # Ensure absolute URL
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            url = urljoin(base_url, url)
        elif not url.startswith('http'):
            url = 'https://' + url
        
        return url.strip()
    
    def extract_contact_details(self, business: Dict) -> Dict:
        """Extract contact details from business website"""
        website = business.get('website', '')
        business_name = business.get('name', '')
        
        if not website or not self.is_valid_url(website):
            return business
        
        try:
            # Fetch main page
            response = self.session.get(website, timeout=15, allow_redirects=True)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text()
            
            # Extract emails
            emails = self.extract_emails(page_text)
            email = emails[0] if emails else ""
            
            # Extract social media
            social_data = self.extract_social_media(soup, website)
            
            # Try contact page if no social media found
            if not any(social_data.values()):
                social_data = self.extract_from_contact_page(soup, website)
            
            # Update business with extracted data
            business.update({
                'email': email,
                'facebook': social_data['facebook'],
                'instagram': social_data['instagram'],
                'twitter': social_data['twitter'],
                'linkedin': social_data['linkedin'],
                'youtube': social_data['youtube'],
                'whatsapp': social_data['whatsapp']
            })
            
            logger.info(f"Extracted contact details for {business_name}: Email={bool(email)}, Social={sum(bool(v) for v in social_data.values())}")
            
        except Exception as e:
            logger.warning(f"Error extracting contact details from {website}: {e}")
        
        return business
    
    def extract_from_contact_page(self, soup: BeautifulSoup, base_url: str) -> Dict[str, str]:
        """Extract social media from contact/about pages with enhanced detection"""
        social_data = {
            'facebook': '', 'instagram': '', 'twitter': '', 
            'linkedin': '', 'youtube': '', 'whatsapp': ''
        }
        
        # Enhanced contact page link detection
        contact_keywords = [
            'contact', 'about', 'info', 'information', 'reach', 'connect',
            'support', 'help', 'team', 'staff', 'people', 'company',
            'business', 'services', 'location', 'address', 'phone',
            'email', 'social', 'media', 'follow', 'connect'
        ]
        
        contact_links = []
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '').lower()
            text = link.get_text().lower()
            
            # Check if link contains contact-related keywords
            if any(keyword in href or keyword in text for keyword in contact_keywords):
                contact_links.append(link['href'])
        
        # Also look for contact information in page content
        page_text = soup.get_text().lower()
        if any(keyword in page_text for keyword in ['contact us', 'get in touch', 'reach us', 'call us']):
            # If contact info is on main page, extract from there
            contact_social = self.extract_social_media(soup, base_url)
            for platform, url in contact_social.items():
                if url and not social_data[platform]:
                    social_data[platform] = url
        
        # Try each contact page (limit to 5 attempts)
        for contact_link in contact_links[:5]:
            try:
                if not contact_link.startswith('http'):
                    if contact_link.startswith('/'):
                        contact_url = base_url.rstrip('/') + contact_link
                    else:
                        contact_url = base_url.rstrip('/') + '/' + contact_link
                else:
                    contact_url = contact_link
                
                contact_response = self.session.get(contact_url, timeout=10)
                contact_soup = BeautifulSoup(contact_response.text, 'html.parser')
                
                # Extract social media from contact page
                contact_social = self.extract_social_media(contact_soup, contact_url)
                
                # Update with found data
                for platform, url in contact_social.items():
                    if url and not social_data[platform]:
                        social_data[platform] = url
                
                # If we found something, break
                if any(social_data.values()):
                    break
                    
            except Exception as e:
                logger.debug(f"Error accessing contact page {contact_link}: {e}")
                continue
        
        return social_data

# Global extractor instance
extractor = ContactDetailsExtractor()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "contact-details-server",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/enrich', methods=['POST'])
def enrich_businesses():
    """Enrich business data with contact details"""
    try:
        data = request.get_json()
        businesses = data.get('businesses', [])
        
        if not businesses:
            return jsonify({"error": "No businesses provided"}), 400
        
        logger.info(f"Received {len(businesses)} businesses for enrichment")
        
        # Process businesses with threading for better performance
        enriched_businesses = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # Submit all businesses for processing
            future_to_business = {
                executor.submit(extractor.extract_contact_details, business): business 
                for business in businesses
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_business):
                business = future_to_business[future]
                try:
                    enriched_business = future.result()
                    enriched_businesses.append(enriched_business)
                except Exception as e:
                    logger.error(f"Error processing business {business.get('name', 'unknown')}: {e}")
                    enriched_businesses.append(business)  # Add original business
        
        logger.info(f"Successfully enriched {len(enriched_businesses)} businesses")
        
        return jsonify({
            "success": True,
            "businesses": enriched_businesses,
            "total_enriched": len(enriched_businesses),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in enrich endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/extract-single', methods=['POST'])
def extract_single_business():
    """Extract contact details for a single business"""
    try:
        data = request.get_json()
        business = data.get('business', {})
        
        if not business:
            return jsonify({"error": "No business provided"}), 400
        
        enriched_business = extractor.extract_contact_details(business)
        
        return jsonify({
            "success": True,
            "business": enriched_business,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in extract-single endpoint: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    logger.info("Starting Contact Details Server...")
    logger.info("Available endpoints:")
    logger.info("  GET  /health - Health check")
    logger.info("  POST /enrich - Enrich multiple businesses")
    logger.info("  POST /extract-single - Extract contact details for single business")
    
    # Use PORT from environment (Railway requirement)
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False) 
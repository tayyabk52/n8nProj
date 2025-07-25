# 🚀 Google Maps Scraper - Dual Server Architecture

A sophisticated Google Maps business scraper with intelligent contact details extraction using a dual-server architecture.

## 🏗️ Architecture Overview

### **Server 1: Main Scraper (Port 5000)**
- **Purpose**: Google Maps business discovery and basic data extraction
- **Responsibilities**:
  - Scrape business listings from Google Maps
  - Extract basic information (name, address, phone, website, rating)
  - Handle scrolling and pagination
  - Manage duplicate detection
  - **NO** social media extraction at this level

### **Server 2: Contact Details Server (Port 5001)**
- **Purpose**: Intelligent contact details extraction from business websites
- **Responsibilities**:
  - Receive business list from main server
  - Scrape business websites for contact details
  - Extract and validate social media links
  - Extract email addresses
  - Return enriched business data

## 🚀 Quick Start

### **Option 1: Use the Launcher (Recommended)**
```bash
python launcher.py
```
This will start both servers automatically and run a test.

### **Option 2: Manual Start**
```bash
# Terminal 1 - Start main scraper server
python main.py

# Terminal 2 - Start contact details server
python contact_server.py
```

## 📋 API Endpoints

### **Main Server (Port 5000)**
- `GET /health` - Health check
- `POST /scrape` - Scrape businesses with contact enrichment
- `POST /scrape-batch` - Batch scraping
- `POST /restart-driver` - Restart browser driver

### **Contact Details Server (Port 5001)**
- `GET /health` - Health check
- `POST /enrich` - Enrich business list with contact details
- `POST /extract-single` - Extract contact details for single business

## 🔧 Configuration

### **Scraper Settings**
Edit `scraper_settings.json` or use the GUI:
```bash
python gui_settings.py
```

### **Key Settings**
- `headless_mode`: Run browser in background
- `scroll_attempts`: Number of scroll attempts
- `max_results`: Maximum businesses to extract
- `debug_mode`: Enable detailed logging

## 📊 Usage Examples

### **Basic Scraping Request**
```bash
curl -X POST http://127.0.0.1:5000/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "search_term": "car rental",
    "area_name": "DHA Phase 1",
    "latitude": 31.4704,
    "longitude": 74.4136,
    "radius_km": 5,
    "max_results": 20
  }'
```

### **Response Format**
```json
{
  "success": true,
  "data": {
    "businesses": [
      {
        "name": "Business Name",
        "address": "Business Address",
        "phone": "Phone Number",
        "website": "https://website.com",
        "email": "contact@business.com",
        "facebook": "https://facebook.com/business",
        "instagram": "https://instagram.com/business",
        "twitter": "https://twitter.com/business",
        "linkedin": "https://linkedin.com/company/business",
        "youtube": "https://youtube.com/business",
        "whatsapp": "https://wa.me/business",
        "rating": "4.5",
        "review_count": "123",
        "category": "Business Category",
        "search_term": "car rental",
        "area": "DHA Phase 1",
        "coordinates": "31.4704,74.4136",
        "scraped_date": "2025-07-24"
      }
    ],
    "total_found": 20,
    "search_term": "car rental",
    "area": "DHA Phase 1",
    "coordinates": "31.4704,74.4136",
    "scraped_at": "2025-07-24T16:15:25.493014"
  },
  "timestamp": "2025-07-24T16:15:25.507606"
}
```

## 🔍 Features

### **Intelligent Contact Extraction**
- **Email Detection**: Advanced regex patterns for email extraction
- **Social Media Validation**: Prevents generic/placeholder URLs
- **Website Scraping**: Multi-page contact detail extraction
- **Error Handling**: Graceful fallbacks for failed requests

### **Advanced Scraping**
- **Playwright Integration**: Modern browser automation
- **Smart Scrolling**: Dynamic content loading
- **Duplicate Detection**: Fuzzy matching for business deduplication
- **Quality Filtering**: Minimum data quality requirements

### **Performance Optimizations**
- **Threading**: Parallel contact detail extraction
- **Connection Pooling**: Efficient HTTP requests
- **Caching**: Session-based request optimization
- **Timeout Management**: Configurable request timeouts

## 🛠️ Installation

### **1. Install Dependencies**
```bash
pip install -r requirements.txt
```

### **2. Install Playwright Browsers**
```bash
playwright install
```

### **3. Download NLTK Data**
```python
import nltk
nltk.download('punkt')
nltk.download('stopwords')
```

## 🔧 Troubleshooting

### **Common Issues**

#### **Server Not Starting**
- Check if ports 5000 and 5001 are available
- Ensure all dependencies are installed
- Check firewall settings

#### **Contact Details Not Extracted**
- Verify contact details server is running
- Check website accessibility
- Review server logs for errors

#### **Low Success Rate**
- Adjust `scroll_attempts` in settings
- Increase `max_results` for more data
- Check network connectivity

### **Logs and Debugging**
- Enable `debug_mode` in settings
- Check console output for detailed logs
- Monitor server health endpoints

## 📈 Performance Tips

### **For High-Volume Scraping**
1. **Increase Threads**: Modify `max_workers` in contact server
2. **Optimize Timeouts**: Adjust request timeouts based on network
3. **Batch Processing**: Use `/scrape-batch` for multiple locations
4. **Caching**: Implement result caching for repeated queries

### **For Better Contact Extraction**
1. **Valid Websites**: Ensure businesses have accessible websites
2. **Social Media**: Look for businesses with active social presence
3. **Contact Pages**: Many businesses have dedicated contact pages
4. **Email Patterns**: Common patterns like `info@`, `contact@`, `hello@`

## 🔒 Security Considerations

- **Rate Limiting**: Implement request rate limiting
- **User Agents**: Rotate user agents to avoid detection
- **Proxies**: Use proxy rotation for large-scale scraping
- **Respect Robots.txt**: Check website robots.txt files
- **Terms of Service**: Ensure compliance with website ToS

## 📝 License

This project is for educational and research purposes. Please respect website terms of service and implement appropriate rate limiting for production use.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review server logs
3. Test with minimal data first
4. Create an issue with detailed information 
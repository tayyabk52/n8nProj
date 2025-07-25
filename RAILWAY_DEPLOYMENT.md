# Railway Deployment Guide

## Overview
This guide explains how to deploy the Google Maps Scraper on Railway with both the main server and contact details server.

## Architecture
- **Main Server**: Handles Google Maps scraping (Port 5000)
- **Contact Server**: Enriches businesses with contact details (Port 5001)

## Option 1: Single Service Deployment (Recommended)

### Step 1: Create Railway Project
1. Go to [Railway.app](https://railway.app)
2. Sign up/Login with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repository

### Step 2: Configure Environment Variables
In Railway dashboard, go to your project → Variables tab and add:

```
PORT=5000
CONTACT_SERVER_URL=https://your-contact-service-url.railway.app
```

### Step 3: Deploy
Railway will automatically detect the `Procfile` and deploy your main server.

## Option 2: Two-Service Deployment

### Service 1: Main Server
1. Create new Railway project for main server
2. Use `Procfile` (runs `python main.py`)
3. Set environment variables:
   ```
   PORT=5000
   CONTACT_SERVER_URL=https://your-contact-service-url.railway.app
   ```

### Service 2: Contact Server
1. Create another Railway project for contact server
2. Rename `Procfile.contact` to `Procfile`
3. Set environment variables:
   ```
   PORT=5001
   ```

## Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `PORT` | Server port | 5000/5001 | Yes |
| `CONTACT_SERVER_URL` | URL of contact server | http://127.0.0.1:5001 | No |

## Testing Your Deployment

### Health Check
```bash
curl https://your-app.railway.app/health
```

### Test Scraping
```bash
curl -X POST https://your-app.railway.app/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "search_term": "car rental",
    "area_name": "Karachi",
    "latitude": 24.8607,
    "longitude": 67.0011,
    "radius_km": 5,
    "max_results": 10
  }'
```

## Troubleshooting

### Common Issues

1. **Port Binding Error**
   - Ensure `host='0.0.0.0'` in both servers
   - Use `PORT` environment variable

2. **Contact Server Connection Error**
   - Verify `CONTACT_SERVER_URL` is correct
   - Check if contact server is running

3. **Chrome/Playwright Issues**
   - Railway may have limitations with browser automation
   - Consider using headless mode only

### Logs
Check Railway logs in the dashboard for detailed error messages.

## Cost Optimization

- Railway offers 500 hours/month free
- Consider using single service deployment to save resources
- Monitor usage in Railway dashboard

## Security Notes

- Never commit API keys or sensitive data
- Use Railway's environment variables for secrets
- Consider rate limiting for production use 
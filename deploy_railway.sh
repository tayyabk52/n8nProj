#!/bin/bash

echo "🚂 Railway Deployment Script"
echo "============================"

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "❌ Git repository not found. Please initialize git first:"
    echo "   git init"
    echo "   git add ."
    echo "   git commit -m 'Initial commit'"
    exit 1
fi

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "📦 Installing Railway CLI..."
    npm install -g @railway/cli
fi

echo "✅ Railway CLI is installed"

# Check if user is logged in to Railway
if ! railway whoami &> /dev/null; then
    echo "🔐 Please login to Railway:"
    railway login
fi

echo "✅ Logged in to Railway"

echo ""
echo "📋 Next Steps:"
echo "1. Create a new Railway project: railway init"
echo "2. Deploy your app: railway up"
echo "3. Set environment variables in Railway dashboard"
echo "4. Get your app URL: railway domain"
echo ""
echo "📖 For detailed instructions, see RAILWAY_DEPLOYMENT.md"
echo ""
echo "🔧 Environment Variables to set:"
echo "   PORT=5000"
echo "   CONTACT_SERVER_URL=https://your-contact-service-url.railway.app" 